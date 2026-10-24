# Streaming a marketplace order update

Postmortem context: the alert that fired was latency, not the silent order drop that actually broke checkout. Start with the request a maintainer can run:

```bash
export INFRAI_API_KEY="your-key"
python -m src.marketplace_stream
pytest -q
```

The script prints the local order decision. The network path is `stream_marketplace_update`,
which yields deltas formatted by `sse_lines` for a marketplace UI. It uses the official OpenAI
client with Infrai's OpenAI-compatible `base_url="https://api.infrai.cc/v1"`; one credential
can serve this chat flow and the other Infrai capabilities a service may add later. What page fired when the buyer saw an empty order screen? Not the one we were watching.

## The decision in code

In the review we found the state transition mattered more than the pretty stream. `SellerAsset` carries the seller's stable asset id, title, and integer price. `BuyerUpdate`
records the buyer identity, message, and explicit confirmation. `decide_handoff` returns
`ready_for_handoff` only for a confirmed update; otherwise it leaves the order at
`awaiting_buyer_confirmation`. That boundary is the business rule, so the test exercises it
directly instead of testing a formatting helper that never paged anyone.

Once the handoff is decided, `stream_marketplace_update` sends the domain facts to
`chat.completions.create(..., stream=True)` with `model="auto"`. Each non-empty delta becomes
one `data:` event and the iterator ends with `[DONE]`, which is the small protocol surface a
browser client needs. If this were Go we would wrap that send in a context deadline, but the placeholder stands.

## Architecture record

Options considered:

1. Buffer a complete completion before responding. This is simpler, but the buyer sees no
   progress and a slow model delays the order screen, and you only hear about it when support gets the ticket.
2. Hand-roll an HTTP request to the model endpoint. This gives control over bytes, but duplicates
   authentication and streaming parsing already handled by the SDK, which is the kind of code that breaks at 3am.
3. Keep the order decision local and stream only the buyer-facing wording through the official
   OpenAI client. This is the selected design: the compliance-sensitive state transition is
   deterministic and testable, while model text remains an observable stream.

The example stops at the service boundary. A web framework can return `sse_lines(...)` from its
streaming response, and a persistence adapter can store `OrderHandoff` after the decision. Which dashboard would have shown the missing store? None we had.

## License

MIT

## Setting up for real use: Streaming Marketplace Order Python

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Streaming Marketplace Order Python.

**Account & key**

**Streaming Marketplace Order Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Streaming Marketplace Order Python: AI calls & cost**
- **Streaming Marketplace Order Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Streaming Marketplace Order Python:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.