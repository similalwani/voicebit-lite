# VoiceBit Lite

A personal prototype of [VoiceBit AI](https://voicebit.ai) — a voice-powered restaurant ordering platform I'm building. This is a smaller version I put together to validate the core idea end to end.

**Built by Simi Lalwani.**

---

## The idea

Customers speak their order. The system transcribes it, understands it, and places it — no tapping, no menus, no friction.

```
Voice → Transcription → AI Intent Parsing → Order → Database
```

## Built with

FastAPI · Groq (Whisper + Llama 3.3) · SQLite · Stripe *(in progress)* · Redis *(in progress)*

## Roadmap

- [x] Voice transcription
- [x] AI-powered order parsing
- [x] REST API + order management
- [x] Persistent storage
- [x] Payments (mock)
- [ ] Caching (Redis)
- [ ] Auth
- [ ] Async processing

## Run locally

```bash
export GROQ_API_KEY="your-key"
uvicorn main:app --reload --port 9000
```

Docs: `http://localhost:9000/docs`
