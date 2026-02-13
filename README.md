# Y-Connect WhatsApp Bot

A WhatsApp-based conversational AI system that helps Indian citizens discover government schemes using natural language queries in their preferred language.

## 🌟 Features

- **Multi-Language Support**: Communicate in 10 Indian languages (Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi)
- **RAG-Based Retrieval**: Accurate scheme information using Retrieval-Augmented Generation
- **Natural Language Processing**: Understand queries in conversational language
- **Context-Aware**: Maintains conversation history and user context
- **Real-Time Responses**: Fast responses via WhatsApp Business API
- **Privacy-First**: Automatic session expiry and PII anonymization
- **Scalable Architecture**: Docker-based deployment with monitoring

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- WhatsApp Business API credentials
- LLM API key (OpenAI, Anthropic, etc.)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/y-connect-whatsapp-bot.git
cd y-connect-whatsapp-bot

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start services
docker-compose up -d

# Import government schemes
docker exec -it y-connect-app python scripts/import_schemes.py

# Check health
curl http://localhost:8000/health
```

See [Quick Start Guide](docs/QUICK_START.md) for detailed instructions.

## 📚 Documentation

- [Deployment Guide](docs/DEPLOYMENT.md) - Complete deployment instructions
- [Quick Start Guide](docs/QUICK_START.md) - Get started in 10 minutes
- [Environment Variables](docs/ENVIRONMENT_VARIABLES.md) - Configuration reference
- [Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md) - Pre-launch checklist

## 🏗️ Architecture

```
┌─────────────┐
│   WhatsApp  │
│    Users    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│     WhatsApp Business API (Webhook)     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│         Y-Connect Application            │
│  ┌────────────────────────────────────┐  │
│  │  Language Detector                 │  │
│  │  Query Processor                   │  │
│  │  RAG Engine                        │  │
│  │  Response Generator                │  │
│  └────────────────────────────────────┘  │
└───┬──────────┬──────────┬────────────────┘
    │          │          │
    ▼          ▼          ▼
┌─────────┐ ┌──────┐ ┌─────────┐
│PostgreSQL│ │Redis │ │ Qdrant  │
│         │ │      │ │ Vector  │
│ Schemes │ │Session│ │  Store  │
└─────────┘ └──────┘ └─────────┘
```

## 🛠️ Technology Stack

- **Backend**: Python 3.11, FastAPI
- **Database**: PostgreSQL 14
- **Cache**: Redis 7
- **Vector Store**: Qdrant
- **Embeddings**: sentence-transformers
- **LLM**: OpenAI GPT-4 / Anthropic Claude / Custom
- **Testing**: pytest, Hypothesis (property-based testing)
- **Monitoring**: Prometheus, Grafana
- **Deployment**: Docker, Docker Compose

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run property-based tests
pytest -m property

# Run specific test file
pytest tests/test_language_detector.py
```

## 📊 Monitoring

Access monitoring dashboards:

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# Metrics: http://localhost:8000/metrics
```

## 🔒 Security

- HTTPS enforcement in production
- Webhook signature verification
- PII anonymization in logs
- Session data auto-expiry (24 hours)
- Secure environment variable management
- Rate limiting and DDoS protection

## 🌍 Supported Languages

| Language   | Code | Native Name |
|------------|------|-------------|
| Hindi      | hi   | हिन्दी      |
| English    | en   | English     |
| Tamil      | ta   | தமிழ்       |
| Telugu     | te   | తెలుగు      |
| Bengali    | bn   | বাংলা       |
| Marathi    | mr   | मराठी       |
| Gujarati   | gu   | ગુજરાતી     |
| Kannada    | kn   | ಕನ್ನಡ       |
| Malayalam  | ml   | മലയാളം      |
| Punjabi    | pa   | ਪੰਜਾਬੀ      |

## 📈 Performance

- Response time: <10 seconds (95th percentile)
- Concurrent users: 100+
- Language detection: >90% accuracy
- RAG retrieval: <2 seconds
- Session management: 24-hour TTL

## 🤝 Contributing

Contributions are welcome! Please read our Contributing Guide for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- WhatsApp Business API for messaging platform
- OpenAI/Anthropic for LLM capabilities
- Qdrant for vector search
- Indian government for scheme data

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/y-connect-whatsapp-bot/issues)
- **Email**: support@y-connect.example.com

## 🗺️ Roadmap

- [ ] Voice message support
- [ ] Image-based scheme discovery
- [ ] Multi-turn clarification dialogs
- [ ] Personalized scheme recommendations
- [ ] Integration with government portals
- [ ] Mobile app companion
- [ ] Analytics dashboard

---

Made with ❤️ for Indian citizens
