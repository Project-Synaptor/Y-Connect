# 🇮🇳 Y-Connect: The Voice-First Government "Buddy"

**Team Name:** GitHappens  
**Team Leader:** Tushar Singh  
**Hackathon:** AI for Bharat Hackathon (Powered by AWS)  
**Track:** AI for Communities, Access & Public Impact  

---

## 🎯 The Problem: Bridging the "Last Mile"

Currently, rural citizens face massive hurdles when trying to access government schemes. Government websites are complex, require English literacy, and often demand 4G internet and PDF downloads. This creates a severe "Digital Divide" where the people who need financial assistance the most are the least equipped to navigate the portals.

## 🚀 The Solution: Y-Connect

Y-Connect is an AI-powered WhatsApp agent that helps rural users find and apply for government schemes using natural language. Unlike complex web portals, Y-Connect operates entirely within WhatsApp. It requires zero new app installs, works perfectly on low-end smartphones over basic 2G/3G networks, and eliminates the literacy barrier by interacting with users exactly where they are already comfortable.

---

## 🏗️ Current MVP Architecture (Live & Deployed)

For the hackathon submission, we focused on building a bulletproof, highly scalable cloud backend capable of processing concurrent WhatsApp messages with extremely low latency.

* **The Gateway:** Twilio WhatsApp Business API webhook integration.
* **The Orchestrator:** Asynchronous Python FastAPI server.
* **The Memory:** Redis for connection pooling, load monitoring, and queue management.
* **The Knowledge Base:** Qdrant Vector Database populated with real government scheme data.
* **The Brain:** Amazon Bedrock (Nova Lite) acting as the RAG reasoning engine to generate highly contextual, accurate, markdown-formatted scheme guides.
* **The Infrastructure:** Fully containerized via Docker Compose and deployed live on an **AWS EC2 instance**.

## 🗺️ Phase 2 Roadmap (The Multimodal Vision)

With the foundational RAG pipeline stabilized, our immediate development roadmap introduces frugal engineering and full multimodal accessibility:

1. **Native Language Voice & Text Output:** Integrating **OpenAI Whisper** and **AWS Polly** to allow users to send voice notes in local dialects (Hindi, Odia, Bhojpuri). The AI will maintain the language state and return both a **playable audio reply** and a **detailed text guide** entirely in the user's native language.

2. **Ultra-Low Latency C-Layer:** A custom C-language shared library (`.so`) bound via `ctypes` that acts as a 0.01ms "Desi Safety Filter" to block spam/unsafe queries locally *before* they hit the expensive cloud LLM, reducing API costs by 40%.

3. **Instant Document Vision (OCR):** Allowing users to snap photos of Income Certificates to automatically extract eligibility data.

4. **Auto-Form Generation:** Generating pre-filled PDF application forms directly within the WhatsApp chat.

---

## 🛠️ Tech Stack

* **Backend:** Python, FastAPI, Docker, Docker Compose
* **Databases:** Qdrant (Vector), PostgreSQL (Relational), Redis (Queue)
* **AI/LLM:** Amazon Bedrock (Nova Lite v1:0)
* **Cloud & DevOps:** Amazon Web Services (EC2, IAM), Kiro.dev (Spec-Driven Dev)
* **Integrations:** Twilio (WhatsApp API)

---

## 💻 Local Setup & Deployment

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/Y-Connect.git
cd Y-Connect
```

2. **Configure Environment:**

Create a `.env` file and add your AWS, Twilio, Redis, and Postgres credentials. Ensure `AWS_DEFAULT_REGION="us-east-1"` is set for Amazon Nova access.

3. **Deploy the Engine:**

```bash
# Launch the microservices in detached mode
sudo docker-compose up -d --build app
```

4. **Ingest Scheme Data:**

```bash
# Populate the Qdrant Vector DB with scheme data
sudo docker-compose exec app python -m scripts.execute_hybrid_approach
```

5. **Expose Webhook:**

Link your server's public IP (e.g., `http://YOUR_EC2_IP:8000/twilio`) to your Twilio Sandbox settings.

---

## 🙏 Acknowledgments

Built with passion for bridging India's digital divide. Special thanks to AWS, Twilio, and the open-source community.

---

Made with ❤️ for Bharat
