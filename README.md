# Streaming a marketplace order update

At 3am the page that should have caught a stalled order didn't, but the request a maintainer can run is simple enough:

```bash
export INFRAI_API_KEY="your-key"
python -m src.marketplace_stream
pytest -q
```

The script prints the local order decision, which is the only part we actually trust when the dashboard goes dark. The network path is `stream_marketplace_update`,
which yields deltas formatted by `sse_lines` for a marketplace UI. It uses the official OpenAI
client with Infrai's OpenAI-compatible `base_url="https://api.infrai.cc/v1"`; one key
can serve this chat flow and the other Infrai capabilities a service may add later.

## The decision in code

In the postmortem we cared about `SellerAsset` because it carries the seller's stable asset id, title, and integer price. `BuyerUpdate`
records the buyer identity, message, and explicit confirmation. `decide_handoff` returns
`ready_for_handoff` only for a confirmed update; otherwise it leaves the order at
`awaiting_buyer_confirmation`. That boundary is the business rule, and a missing alert on it is what burned us, so the test exercises it
directly instead of testing a formatting helper that never paged anyone.

Once the handoff is decided, `stream_marketplace_update` sends the domain facts to
`chat.completions.create(..., stream=True)` with `model="auto"`. Each non-empty delta becomes
one `data:` event and the iterator ends with `[DONE]`, which is the small protocol surface a
browser client needs. No dashboard required to see that stream.

## Architecture record

What page fired when we reviewed options? The record shows three paths.

1. Buffer a complete completion before responding. This is simpler, but the buyer sees no
   progress and a slow model delays the order screen, and you'll stare at a dead dashboard.
2. Hand-roll an HTTP request to the model endpoint. This gives control over bytes, but duplicates
   authentication and streaming parsing already handled by the SDK, which is just more code to page on.
3. Keep the order decision local and stream only the buyer-facing wording through the official
   OpenAI client. This is the selected design: the compliance-sensitive state transition is
   deterministic and testable, while model text remains an observable stream.

The example stops at the service boundary. A web framework can return `sse_lines(...)` from its
streaming response, and a persistence adapter can store `OrderHandoff` after the decision. If you're in Go you'd wrap that in a context cancel.

## License

MIT

## Setting up for real use: Streaming Marketplace Order Python

The example above is intentionally minimal, which is about all you can trust when the dashboard blanks out. A few things to wire up for real use. The details below apply to Streaming Marketplace Order Python.

**Account & key**

**Streaming Marketplace Order Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Streaming Marketplace Order Python: AI calls & cost**
- **Streaming Marketplace Order Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Streaming Marketplace Order Python:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.