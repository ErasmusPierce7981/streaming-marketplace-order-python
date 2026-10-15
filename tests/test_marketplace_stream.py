from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketplace_stream import BuyerUpdate, SellerAsset, decide_handoff, stream_marketplace_update


def test_confirmation_is_required_before_order_handoff():
    asset = SellerAsset("asset-42", "Compliance checklist", 1200)
    waiting = BuyerUpdate("buyer-7", "I have a question.", False)
    confirmed = BuyerUpdate("buyer-7", "I confirm this asset.", True)

    assert decide_handoff(asset, waiting).status == "awaiting_buyer_confirmation"
    assert decide_handoff(asset, confirmed).status == "ready_for_handoff"


def test_stream_skips_chunks_without_choices():
    asset = SellerAsset("asset-42", "Compliance checklist", 1200)
    update = BuyerUpdate("buyer-7", "I confirm this asset.", True)
    chunks = [
        SimpleNamespace(choices=[]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Ready"))]),
        SimpleNamespace(choices=[]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]),
    ]
    with patch.dict("os.environ", {"INFRAI_API_KEY": "test-key"}), patch(
        "src.marketplace_stream.OpenAI"
    ) as client:
        client.return_value.chat.completions.create.return_value = iter(chunks)
        assert list(stream_marketplace_update(asset, update, decide_handoff(asset, update))) == [
            "Ready"
        ]
