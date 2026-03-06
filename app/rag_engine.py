"""RAG Engine component for Y-Connect WhatsApp Bot

Handles retrieval-augmented generation for scheme information.
Retrieves relevant schemes using semantic search and generates responses using LLM.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import os

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from app.models import ProcessedQuery, SchemeDocument, Scheme, SchemeStatus
from app.scheme_vector_store import SchemeVectorStore
from app.scheme_repository import SchemeRepository
from app.config import get_settings
from app.metrics import metrics_tracker

logger = logging.getLogger(__name__)


class GeneratedResponse:
    """Model for LLM-generated responses"""
    
    def __init__(
        self,
        text: str,
        sources: List[SchemeDocument],
        language: str,
        confidence: float = 1.0
    ):
        """
        Initialize generated response
        
        Args:
            text: Generated response text
            sources: Source scheme documents used
            language: Response language
            confidence: Confidence score (0.0 to 1.0)
        """
        self.text = text
        self.sources = sources
        self.language = language
        self.confidence = confidence


class RAGEngine:
    """
    Core retrieval and generation logic for scheme information.
    
    Implements:
    - Semantic search for relevant schemes
    - Context-aware reranking based on user eligibility
    - LLM-based response generation
    - Active scheme prioritization
    """
    
    def __init__(
        self,
        vector_store: Optional[SchemeVectorStore] = None,
        scheme_repository: Optional[SchemeRepository] = None
    ):
        """
        Initialize RAG Engine
        
        Args:
            vector_store: SchemeVectorStore instance (creates new if None)
            scheme_repository: SchemeRepository instance (uses default if None)
        """
        self.settings = get_settings()
        
        # Initialize vector store
        if vector_store is None:
            self.vector_store = SchemeVectorStore()
        else:
            self.vector_store = vector_store
        
        # Initialize scheme repository
        if scheme_repository is None:
            self.scheme_repository = SchemeRepository()
        else:
            self.scheme_repository = scheme_repository
        
        # Initialize AWS Bedrock client for LLM
        if BOTO3_AVAILABLE:
            try:
                self.bedrock_client = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=os.getenv('AWS_REGION', 'us-east-1'),
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                )
                logger.info("Initialized AWS Bedrock client for Nova Lite")
            except Exception as e:
                logger.warning(f"Failed to initialize Bedrock client: {e}")
                self.bedrock_client = None
        else:
            logger.warning("boto3 not available, Bedrock client not initialized")
            self.bedrock_client = None
        
        logger.info("Initialized RAGEngine")
    
    def retrieve_schemes(
        self,
        query: ProcessedQuery,
        top_k: Optional[int] = None
    ) -> List[SchemeDocument]:
        """
        Retrieve relevant schemes using semantic search
        
        Args:
            query: Processed query with embeddings
            top_k: Number of top results to retrieve (defaults to config)
            
        Returns:
            List of relevant scheme documents with similarity scores
        """
        start_time = time.time()
        
        if top_k is None:
            top_k = self.settings.rag_top_k_results
        
        try:
            # Build metadata filters from query entities
            filters = self._build_filters(query.entities)
            
            # Perform semantic search
            scheme_docs = self.vector_store.search_schemes(
                query=query.original_text,
                top_k=top_k * 2,  # Retrieve more for reranking
                language=query.language,
                filters=filters,
                confidence_threshold=None  # Apply threshold after reranking
            )
            
            # Enrich scheme documents with full scheme data from database
            enriched_docs = self._enrich_scheme_documents(scheme_docs)
            
            # Rerank based on user context
            reranked_docs = self.rerank_results(query, enriched_docs)
            
            # Return top_k after reranking
            final_docs = reranked_docs[:top_k]
            
            # Track metrics
            duration = time.time() - start_time
            if final_docs:
                metrics_tracker.track_scheme_retrieval_success(duration)
            else:
                metrics_tracker.track_scheme_retrieval_failure(reason="no_results")
            
            logger.info(
                f"Retrieved {len(final_docs)} schemes for query: '{query.original_text[:50]}...'"
            )
            
            return final_docs
        
        except Exception as e:
            duration = time.time() - start_time
            metrics_tracker.track_scheme_retrieval_failure(reason="error")
            logger.error(f"Error retrieving schemes: {e}")
            raise
    
    def rerank_results(
        self,
        query: ProcessedQuery,
        candidates: List[SchemeDocument]
    ) -> List[SchemeDocument]:
        """
        Rerank retrieved documents based on user context
        
        Applies:
        - Active scheme prioritization (applied first to ensure boost)
        - Eligibility filtering (age, location, occupation, income, gender)
        - Relevance score adjustment
        
        Args:
            query: Processed query with user context
            candidates: Initial retrieved documents
            
        Returns:
            Reranked list of documents
        """
        if not candidates:
            return []
        
        scored_candidates = []
        
        for doc in candidates:
            # Start with similarity score (preserve original)
            original_score = doc.similarity_score
            score = original_score
            
            # Apply active scheme boost FIRST (before eligibility)
            # This ensures active schemes always get boosted
            if doc.scheme.status == SchemeStatus.ACTIVE:
                score *= 1.5  # 50% boost for active schemes
            elif doc.scheme.status == SchemeStatus.EXPIRED:
                score *= 0.5  # 50% penalty for expired schemes
            
            # Then apply eligibility boost/penalty
            eligibility_score = self._calculate_eligibility_score(
                doc.scheme,
                query.entities
            )
            score *= eligibility_score
            
            # Store adjusted score
            doc.similarity_score = score
            scored_candidates.append(doc)
        
        # Sort by adjusted score (descending)
        scored_candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        
        logger.debug(f"Reranked {len(scored_candidates)} candidates")
        
        return scored_candidates
    
    async def generate_response(
        self,
        query: ProcessedQuery,
        retrieved_docs: List[SchemeDocument],
        language: str
    ) -> GeneratedResponse:
        """
        Generate natural language response using LLM
        
        Args:
            query: User's processed query
            retrieved_docs: Retrieved scheme documents
            language: Target language for response
            
        Returns:
            Generated response with sources
        """
        try:
            # Check if we have any relevant documents
            if not retrieved_docs:
                return GeneratedResponse(
                    text=self._get_no_results_message(language),
                    sources=[],
                    language=language,
                    confidence=0.0
                )
            
            # Check confidence threshold
            max_confidence = max(doc.similarity_score for doc in retrieved_docs)
            if max_confidence < self.settings.rag_confidence_threshold:
                return GeneratedResponse(
                    text=self._get_low_confidence_message(language),
                    sources=retrieved_docs,
                    language=language,
                    confidence=max_confidence
                )
            
            # Build prompt context
            prompt = self._build_prompt(query, retrieved_docs, language)
            
            # Call LLM API
            response_text = await self._call_llm_api(prompt, language)
            
            return GeneratedResponse(
                text=response_text,
                sources=retrieved_docs,
                language=language,
                confidence=max_confidence
            )
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def _build_filters(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build metadata filters from query entities
        
        Args:
            entities: Extracted entities from query
            
        Returns:
            Dictionary of metadata filters
        """
        filters = {}
        
        # Filter by category if specified
        if "category" in entities:
            filters["category"] = entities["category"]
        
        # Filter by state if specified
        if "location" in entities:
            location = entities["location"]
            if location != "ALL":
                # Will match schemes with this state OR 'ALL'
                filters["state"] = location
        
        # NOTE: Status filter commented out until Qdrant collection has indexes
        # Uncomment after running: python scripts/recreate_qdrant_collection.py
        # filters["status"] = SchemeStatus.ACTIVE.value
        
        return filters
    
    def _enrich_scheme_documents(
        self,
        scheme_docs: List[SchemeDocument]
    ) -> List[SchemeDocument]:
        """
        Enrich scheme documents with full data from database
        
        Args:
            scheme_docs: Scheme documents from vector search
            
        Returns:
            Enriched scheme documents
        """
        enriched_docs = []
        
        for doc in scheme_docs:
            try:
                # Fetch full scheme from database
                full_scheme = self.scheme_repository.get_scheme_by_id(doc.scheme_id)
                
                if full_scheme:
                    # Update document with full scheme data
                    doc.scheme = full_scheme
                    enriched_docs.append(doc)
                else:
                    logger.warning(
                        f"Scheme {doc.scheme_id} not found in database, skipping"
                    )
            except Exception as e:
                logger.error(f"Error enriching scheme {doc.scheme_id}: {e}")
                # Continue with other documents
        
        return enriched_docs
    
    def _calculate_eligibility_score(
        self,
        scheme: Scheme,
        user_context: Dict[str, Any]
    ) -> float:
        """
        Calculate eligibility score based on user context
        
        Uses additive scoring instead of multiplicative to ensure
        matching schemes always rank higher than non-matching ones.
        
        Args:
            scheme: Scheme to evaluate
            user_context: User's context (age, location, occupation, etc.)
            
        Returns:
            Eligibility score multiplier (0.3 to 2.5)
        """
        # If no user context, return neutral score
        if not user_context:
            return 1.0
        
        # Start with base score
        base_score = 1.0
        boost = 0.0
        penalty = 0.0
        
        eligibility = scheme.eligibility_criteria
        
        # Check location eligibility (based on scheme.applicable_states)
        if "location" in user_context:
            user_location = user_context["location"]
            applicable_states = scheme.applicable_states
            
            if "ALL" in applicable_states or user_location in applicable_states:
                boost += 0.5  # Strong boost for location match
            else:
                penalty += 0.4  # Penalty if location doesn't match
        
        # Check other eligibility criteria only if they exist
        if eligibility:
            # Check age eligibility
            if "age" in user_context and "age_min" in eligibility:
                user_age = user_context["age"]
                age_min = eligibility.get("age_min", 0)
                age_max = eligibility.get("age_max", 120)
                
                if age_min <= user_age <= age_max:
                    boost += 0.6  # Strong boost for age match
                else:
                    penalty += 0.5  # Penalty if age doesn't match
            
            # Check occupation eligibility
            if "occupation" in user_context and "occupation" in eligibility:
                required_occupation = eligibility["occupation"]
                user_occupation = user_context["occupation"]
                
                occupation_match = False
                if isinstance(required_occupation, list):
                    occupation_match = user_occupation in required_occupation
                else:
                    occupation_match = user_occupation == required_occupation
                
                if occupation_match:
                    boost += 0.7  # Very strong boost for occupation match
                else:
                    penalty += 0.4  # Penalty for occupation mismatch
            
            # Check gender eligibility
            if "gender" in user_context and "gender" in eligibility:
                required_gender = eligibility["gender"]
                user_gender = user_context["gender"]
                
                if required_gender == "any" or user_gender == required_gender:
                    boost += 0.4  # Boost for gender match
                else:
                    penalty += 0.4  # Penalty if gender doesn't match
            
            # Check income eligibility
            if "income" in user_context and "income_category" in eligibility:
                user_income = user_context["income"]
                required_income = eligibility["income_category"]
                
                if user_income == required_income:
                    boost += 0.5  # Boost for income match
        
        # Calculate final score: base + boost - penalty
        final_score = base_score + boost - penalty
        
        # Clamp score between 0.3 and 2.5
        return max(0.3, min(2.5, final_score))
    
    def _build_prompt(
        self,
        query: ProcessedQuery,
        retrieved_docs: List[SchemeDocument],
        language: str
    ) -> str:
        """
        Build LLM prompt with retrieved documents
        
        Args:
            query: User's processed query
            retrieved_docs: Retrieved scheme documents
            language: Target language
            
        Returns:
            Formatted prompt string
        """
        # Build context from retrieved documents
        context_parts = []
        
        for idx, doc in enumerate(retrieved_docs[:5], 1):  # Limit to top 5
            scheme = doc.scheme
            
            # Get translated content
            scheme_name = scheme.get_translation("scheme_name", language)
            description = scheme.get_translation("description", language)
            benefits = scheme.get_translation("benefits", language)
            application = scheme.get_translation("application_process", language)
            
            context_part = f"""
Scheme {idx}: {scheme_name}
Category: {scheme.category.value}
Status: {scheme.status.value}
Authority: {scheme.authority.value}
States: {', '.join(scheme.applicable_states)}

Description: {description}

Eligibility: {self._format_eligibility(scheme.eligibility_criteria)}

Benefits: {benefits}

How to Apply: {application}

Official URL: {scheme.official_url}
Helpline: {', '.join(scheme.helpline_numbers) if scheme.helpline_numbers else 'Not available'}
"""
            context_parts.append(context_part.strip())
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Build user context string
        user_context_str = self._format_user_context(query.entities)
        
        # Language names mapping
        language_names = {
            "en": "English",
            "hi": "Hindi",
            "ta": "Tamil",
            "te": "Telugu",
            "bn": "Bengali",
            "mr": "Marathi",
            "gu": "Gujarati",
            "kn": "Kannada",
            "ml": "Malayalam",
            "pa": "Punjabi"
        }
        
        language_name = language_names.get(language, "English")
        
        # Build complete prompt
        prompt = f"""You are Y-Connect, a helpful assistant that provides information about Indian government schemes.

User Query: {query.original_text}
User Context: {user_context_str}
Language: {language_name}

Retrieved Schemes:
{context}

Instructions:
1. Answer the user's question based ONLY on the retrieved schemes above
2. Respond in {language_name}
3. Include scheme names and official links
4. Structure response with clear sections: Eligibility, Benefits, How to Apply
5. If multiple schemes match, provide a summary list
6. Keep response under 1600 characters
7. Be conversational and helpful
8. Do not make up information not present in the retrieved schemes

Response:"""
        
        return prompt
    
    def _format_eligibility(self, criteria: Dict[str, Any]) -> str:
        """Format eligibility criteria as readable text"""
        if not criteria:
            return "Not specified"
        
        parts = []
        for key, value in criteria.items():
            if key == "age_min" and "age_max" in criteria:
                parts.append(f"Age: {value}-{criteria['age_max']} years")
            elif key == "age_max":
                continue  # Already handled with age_min
            else:
                parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return ", ".join(parts) if parts else "Not specified"
    
    def _format_user_context(self, entities: Dict[str, Any]) -> str:
        """Format user context as readable text"""
        if not entities:
            return "No specific context provided"
        
        parts = []
        for key, value in entities.items():
            parts.append(f"{key}: {value}")
        
        return ", ".join(parts)
    
    async def _call_llm_api(self, prompt: str, language: str) -> str:
        """
        Call LLM API to generate response using AWS Bedrock Nova Lite
        
        Args:
            prompt: Formatted prompt with context
            language: Target language
            
        Returns:
            Generated response text
        """
        start_time = time.time()
        
        try:
            if not self.bedrock_client:
                raise RuntimeError("Bedrock client not initialized")
            
            # Extract system message and user message from prompt
            # The prompt already contains context, so we use it directly
            system_message = "You are Y-Connect, a helpful, friendly AI assistant for rural India that provides information about government schemes."
            
            # Call AWS Bedrock Nova Lite using converse API
            model_id = 'us.amazon.nova-lite-v1:0'
            
            response = self.bedrock_client.converse(
                modelId=model_id,
                system=[{"text": system_message}],
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                inferenceConfig={
                    "maxTokens": 1000,
                    "temperature": 0.5
                }
            )
            
            # Extract response text
            result = response['output']['message']['content'][0]['text']
            
            duration = time.time() - start_time
            
            # Track successful LLM call
            metrics_tracker.track_llm_call(
                provider="aws_bedrock_nova",
                status="success",
                duration=duration
            )
            
            logger.info(f"Generated response using AWS Bedrock Nova Lite in {duration:.2f}s")
            
            return result.strip()
        
        except Exception as e:
            duration = time.time() - start_time
            metrics_tracker.track_llm_call(
                provider="aws_bedrock_nova",
                status="error",
                duration=duration
            )
            logger.error(f"AWS Bedrock API error: {e}")
            
            # Fallback to a generic error message
            raise RuntimeError(f"Failed to generate response: {e}")
    
    
    def _get_no_results_message(self, language: str) -> str:
        """Get 'no results found' message in target language"""
        messages = {
            "en": "I couldn't find any schemes matching your query. Could you provide more details or try a different search?",
            "hi": "मुझे आपकी क्वेरी से मेल खाने वाली कोई योजना नहीं मिली। क्या आप अधिक विवरण प्रदान कर सकते हैं या कोई अन्य खोज आज़मा सकते हैं?",
            "ta": "உங்கள் வினவலுக்கு பொருந்தும் எந்த திட்டங்களையும் என்னால் கண்டுபிடிக்க முடியவில்லை. மேலும் விவரங்களை வழங்க முடியுமா அல்லது வேறு தேடலை முயற்சிக்க முடியுமா?",
            "te": "మీ ప్రశ్నకు సరిపోయే ఏ పథకాలను నేను కనుగొనలేకపోయాను. మీరు మరిన్ని వివరాలను అందించగలరా లేదా వేరే శోధనను ప్రయత్నించగలరా?",
            "bn": "আমি আপনার প্রশ্নের সাথে মিলে এমন কোনো প্রকল্প খুঁজে পাইনি। আপনি কি আরও বিস্তারিত প্রদান করতে পারেন বা একটি ভিন্ন অনুসন্ধান চেষ্টা করতে পারেন?",
            "mr": "मला तुमच्या क्वेरीशी जुळणारी कोणतीही योजना सापडली नाही. तुम्ही अधिक तपशील देऊ शकता किंवा वेगळा शोध घेऊ शकता का?",
            "gu": "મને તમારી ક્વેરી સાથે મેળ ખાતી કોઈ યોજનાઓ મળી નથી. શું તમે વધુ વિગતો આપી શકો છો અથવા કોઈ અલગ શોધ અજમાવી શકો છો?",
            "kn": "ನಿಮ್ಮ ಪ್ರಶ್ನೆಗೆ ಹೊಂದಿಕೆಯಾಗುವ ಯಾವುದೇ ಯೋಜನೆಗಳನ್ನು ನಾನು ಕಂಡುಹಿಡಿಯಲಾಗಲಿಲ್ಲ. ನೀವು ಹೆಚ್ಚಿನ ವಿವರಗಳನ್ನು ನೀಡಬಹುದೇ ಅಥವಾ ಬೇರೆ ಹುಡುಕಾಟವನ್ನು ಪ್ರಯತ್ನಿಸಬಹುದೇ?",
            "ml": "നിങ്ങളുടെ ചോദ്യവുമായി പൊരുത്തപ്പെടുന്ന ഒരു പദ്ധതികളും എനിക്ക് കണ്ടെത്താനായില്ല. നിങ്ങൾക്ക് കൂടുതൽ വിശദാംശങ്ങൾ നൽകാമോ അല്ലെങ്കിൽ മറ്റൊരു തിരയൽ പരീക്ഷിക്കാമോ?",
            "pa": "ਮੈਨੂੰ ਤੁਹਾਡੀ ਪੁੱਛਗਿੱਛ ਨਾਲ ਮੇਲ ਖਾਂਦੀਆਂ ਕੋਈ ਯੋਜਨਾਵਾਂ ਨਹੀਂ ਮਿਲੀਆਂ। ਕੀ ਤੁਸੀਂ ਹੋਰ ਵੇਰਵੇ ਦੇ ਸਕਦੇ ਹੋ ਜਾਂ ਕੋਈ ਵੱਖਰੀ ਖੋਜ ਕਰ ਸਕਦੇ ਹੋ?"
        }
        
        return messages.get(language, messages["en"])
    
    def _get_low_confidence_message(self, language: str) -> str:
        """Get 'low confidence' message in target language"""
        messages = {
            "en": "I found some schemes but I'm not very confident they match your needs. Could you provide more specific details about what you're looking for?",
            "hi": "मुझे कुछ योजनाएं मिलीं लेकिन मुझे पूरा विश्वास नहीं है कि वे आपकी आवश्यकताओं से मेल खाती हैं। क्या आप इस बारे में अधिक विशिष्ट विवरण प्रदान कर सकते हैं कि आप क्या खोज रहे हैं?",
            "ta": "சில திட்டங்களை நான் கண்டேன் ஆனால் அவை உங்கள் தேவைகளுக்கு பொருந்துகின்றன என்று எனக்கு நம்பிக்கை இல்லை. நீங்கள் எதைத் தேடுகிறீர்கள் என்பது பற்றி மேலும் குறிப்பிட்ட விவரங்களை வழங்க முடியுமா?",
            "te": "నేను కొన్ని పథకాలను కనుగొన్నాను కానీ అవి మీ అవసరాలకు సరిపోతాయని నాకు చాలా నమ్మకం లేదు. మీరు ఏమి వెతుకుతున్నారో దాని గురించి మరింత నిర్దిష్ట వివరాలను అందించగలరా?",
            "bn": "আমি কিছু প্রকল্প খুঁজে পেয়েছি কিন্তু আমি খুব আত্মবিশ্বাসী নই যে তারা আপনার চাহিদা পূরণ করে। আপনি কি খুঁজছেন সে সম্পর্কে আরও নির্দিষ্ট বিবরণ প্রদান করতে পারেন?",
            "mr": "मला काही योजना सापडल्या पण मला खात्री नाही की त्या तुमच्या गरजा पूर्ण करतात. तुम्ही काय शोधत आहात याबद्दल अधिक विशिष्ट तपशील देऊ शकता का?",
            "gu": "મને કેટલીક યોજનાઓ મળી પરંતુ મને ખાતરી નથી કે તે તમારી જરૂરિયાતો સાથે મેળ ખાય છે. તમે શું શોધી રહ્યા છો તે વિશે વધુ ચોક્કસ વિગતો આપી શકો છો?",
            "kn": "ನಾನು ಕೆಲವು ಯೋಜನೆಗಳನ್ನು ಕಂಡುಕೊಂಡಿದ್ದೇನೆ ಆದರೆ ಅವು ನಿಮ್ಮ ಅಗತ್ಯಗಳಿಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತವೆ ಎಂದು ನನಗೆ ಹೆಚ್ಚು ವಿಶ್ವಾಸವಿಲ್ಲ. ನೀವು ಏನು ಹುಡುಕುತ್ತಿದ್ದೀರಿ ಎಂಬುದರ ಕುರಿತು ಹೆಚ್ಚು ನಿರ್ದಿಷ್ಟ ವಿವರಗಳನ್ನು ನೀಡಬಹುದೇ?",
            "ml": "ഞാൻ ചില പദ്ധതികൾ കണ്ടെത്തി, പക്ഷേ അവ നിങ്ങളുടെ ആവശ്യങ്ങളുമായി പൊരുത്തപ്പെടുന്നുവെന്ന് എനിക്ക് വളരെ ആത്മവിശ്വാസമില്ല. നിങ്ങൾ എന്താണ് തിരയുന്നത് എന്നതിനെക്കുറിച്ച് കൂടുതൽ വിശദമായ വിവരങ്ങൾ നൽകാമോ?",
            "pa": "ਮੈਨੂੰ ਕੁਝ ਯੋਜਨਾਵਾਂ ਮਿਲੀਆਂ ਪਰ ਮੈਨੂੰ ਬਹੁਤ ਭਰੋਸਾ ਨਹੀਂ ਹੈ ਕਿ ਉਹ ਤੁਹਾਡੀਆਂ ਲੋੜਾਂ ਨਾਲ ਮੇਲ ਖਾਂਦੀਆਂ ਹਨ। ਕੀ ਤੁਸੀਂ ਇਸ ਬਾਰੇ ਹੋਰ ਖਾਸ ਵੇਰਵੇ ਦੇ ਸਕਦੇ ਹੋ ਕਿ ਤੁਸੀਂ ਕੀ ਲੱਭ ਰਹੇ ਹੋ?"
        }
        
        return messages.get(language, messages["en"])
    
    async def close(self) -> None:
        """Close resources and cleanup"""
        self.vector_store.close()
        logger.info("Closed RAGEngine resources")
