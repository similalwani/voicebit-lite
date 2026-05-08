# VoiceBit Lite - A diminutiive simulation of https://voicebit.ai

A personal prototype of [VoiceBit AI](https://voicebit.ai) — a voice-powered restaurant ordering platform I'm building. This is a smaller version I put together to validate the core idea end to end.

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

- Voice Transcription: Implemented via the /transcribe endpoint using Groq (Whisper).
- AI-Powered Order Parsing: Implemented via the /parse-order endpoint using Groq (Llama 3.3).
- Voice-to-Order Flow: A combined /voice-order endpoint handles transcription, parsing, and order creation in one
     step.
- Order Management API: REST endpoints for creating orders (POST /order), retrieving orders (GET /order/{id}),
     and updating status (PATCH /order/{id}/status).
- Persistent Storage: SQLite is integrated to store orders in an orders.db database.
- Caching: Basic Redis caching is implemented in the GET /order/{order_id} endpoint.
- Payments (Mock): A /pay/{order_id} endpoint simulates payment processing by updating the order status to
     "paid".

## Run locally

```bash
export GROQ_API_KEY="your-key"
uvicorn main:app --reload --port 9000
```

Docs: `http://localhost:9000/docs`
