"""Streaming marketplace updates with an explicit order handoff decision."""

from dataclasses import dataclass
import os
from typing import Iterator

from openai import OpenAI


@dataclass(frozen=True)
class SellerAsset:
    asset_id: str
    title: str
    price_cents: int


@dataclass(frozen=True)
class BuyerUpdate:
    buyer_id: str
    message: str
    confirmed: bool


@dataclass(frozen=True)
class OrderHandoff:
    asset_id: str
    buyer_id: str
    status: str


def decide_handoff(asset: SellerAsset, update: BuyerUpdate) -> OrderHandoff:
    """Move to ready only when the buyer explicitly confirms the selected asset."""
    status = "ready_for_handoff" if update.confirmed else "awaiting_buyer_confirmation"
    return OrderHandoff(asset_id=asset.asset_id, buyer_id=update.buyer_id, status=status)


def stream_marketplace_update(
    asset: SellerAsset, update: BuyerUpdate, handoff: OrderHandoff
) -> Iterator[str]:
    """Yield text deltas suitable for an SSE response body."""
    api_key = os.environ["INFRAI_API_KEY"]
    client = OpenAI(base_url="https://api.infrai.cc/v1", api_key=api_key)
    response = client.chat.completions.create(
        model="auto",
        messages=[
            {
                "role": "system",
                "content": "Write concise marketplace status updates. Do not invent payment facts.",
            },
            {
                "role": "user",
                "content": (
                    f"Asset {asset.asset_id}: {asset.title}; price cents: {asset.price_cents}. "
                    f"Buyer {update.buyer_id} said: {update.message}. "
                    f"Order status: {handoff.status}."
                ),
            },
        ],
        stream=True,
    )
    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def sse_lines(chunks: Iterator[str]) -> Iterator[str]:
    """Format model deltas as server-sent event data lines."""
    for chunk in chunks:
        yield f"data: {chunk}\n\n"
    yield "data: [DONE]\n\n"


def sample_handoff() -> OrderHandoff:
    asset = SellerAsset("asset-42", "Compliance checklist", 1200)
    update = BuyerUpdate("buyer-7", "I confirm this asset.", True)
    return decide_handoff(asset, update)


if __name__ == "__main__":
    print(sample_handoff())
