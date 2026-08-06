"""Checkpoint validation script for WhatsApp integration core logic."""

import sys
import hmac
import hashlib

# Ensure app modules are importable
sys.path.insert(0, ".")

errors = []
passed = []


def check(name, fn):
    try:
        fn()
        passed.append(name)
        print(f"  ✓ {name}")
    except Exception as e:
        errors.append((name, str(e)))
        print(f"  ✗ {name}: {e}")


print("\n=== 1. Import Tests ===")


def import_verify_challenge():
    from app.integrations.whatsapp.meta import verify_challenge
    assert callable(verify_challenge)


def import_validate_signature():
    from app.integrations.whatsapp.meta import validate_signature
    assert callable(validate_signature)


def import_normalize():
    from app.integrations.whatsapp.normalizer import normalize
    assert callable(normalize)


def import_normalized_message():
    from app.integrations.whatsapp.models import NormalizedMessage
    assert NormalizedMessage is not None


check("Import verify_challenge", import_verify_challenge)
check("Import validate_signature", import_validate_signature)
check("Import normalize", import_normalize)
check("Import NormalizedMessage", import_normalized_message)

print("\n=== 2. verify_challenge Tests ===")
from app.integrations.whatsapp.meta import verify_challenge


def test_valid_challenge():
    result = verify_challenge("subscribe", "test_challenge_123", "my_token", "my_token")
    assert result == (200, "test_challenge_123"), f"Expected (200, 'test_challenge_123'), got {result}"


def test_wrong_mode():
    result = verify_challenge("unsubscribe", "challenge", "my_token", "my_token")
    assert result == (403, ""), f"Expected (403, ''), got {result}"


def test_wrong_token():
    result = verify_challenge("subscribe", "challenge", "wrong_token", "my_token")
    assert result == (403, ""), f"Expected (403, ''), got {result}"


def test_no_configured_token():
    result = verify_challenge("subscribe", "challenge", "token", "")
    assert result == (503, ""), f"Expected (503, ''), got {result}"


def test_no_challenge():
    result = verify_challenge("subscribe", None, "my_token", "my_token")
    assert result == (400, ""), f"Expected (400, ''), got {result}"


check("Valid challenge returns (200, challenge)", test_valid_challenge)
check("Wrong mode returns (403, '')", test_wrong_mode)
check("Wrong token returns (403, '')", test_wrong_token)
check("No configured token returns (503, '')", test_no_configured_token)
check("No challenge returns (400, '')", test_no_challenge)

print("\n=== 3. validate_signature Tests ===")
from app.integrations.whatsapp.meta import validate_signature


def test_valid_signature():
    secret = "test_secret"
    body = b'{"test": "payload"}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    header = f"sha256={sig}"
    result = validate_signature(body, header, secret)
    assert result is True, f"Expected True, got {result}"


def test_invalid_signature():
    secret = "test_secret"
    body = b'{"test": "payload"}'
    header = "sha256=deadbeef1234567890"
    result = validate_signature(body, header, secret)
    assert result is False, f"Expected False, got {result}"


def test_missing_signature():
    result = validate_signature(b"body", None, "secret")
    assert result is False, f"Expected False, got {result}"


def test_bad_prefix():
    result = validate_signature(b"body", "md5=abc", "secret")
    assert result is False, f"Expected False, got {result}"


def test_no_app_secret():
    from app.integrations.whatsapp.models import ConfigurationError
    try:
        validate_signature(b"body", "sha256=abc", "")
        assert False, "Should have raised ConfigurationError"
    except ConfigurationError:
        pass


check("Valid signature returns True", test_valid_signature)
check("Invalid signature returns False", test_invalid_signature)
check("Missing signature returns False", test_missing_signature)
check("Bad prefix returns False", test_bad_prefix)
check("Empty app_secret raises ConfigurationError", test_no_app_secret)

print("\n=== 4. normalize Tests ===")
from app.integrations.whatsapp.normalizer import normalize
from app.integrations.whatsapp.models import NormalizedMessage


def test_normalize_text():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "2348001234567",
                        "id": "wamid.abc123",
                        "timestamp": "1700000000",
                        "type": "text",
                        "text": {"body": "Hello world"}
                    }]
                }
            }]
        }]
    }
    result = normalize(payload)
    assert isinstance(result, NormalizedMessage), f"Expected NormalizedMessage, got {type(result)}"
    assert result.sender == "2348001234567"
    assert result.message_id == "wamid.abc123"
    assert result.timestamp == 1700000000
    assert result.message_type == "text"
    assert result.body == "Hello world"
    assert result.media_id is None


def test_normalize_audio():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "2348001234567",
                        "id": "wamid.audio456",
                        "timestamp": "1700000001",
                        "type": "audio",
                        "audio": {"id": "media_id_789", "mime_type": "audio/ogg"}
                    }]
                }
            }]
        }]
    }
    result = normalize(payload)
    assert isinstance(result, NormalizedMessage), f"Expected NormalizedMessage, got {type(result)}"
    assert result.message_type == "audio"
    assert result.media_id == "media_id_789"
    assert result.body is None


def test_normalize_status_update():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "statuses": [{"id": "wamid.abc", "status": "delivered"}]
                }
            }]
        }]
    }
    result = normalize(payload)
    assert result is None, f"Expected None for status update, got {result}"


def test_normalize_malformed():
    result = normalize({})
    assert result is None
    result = normalize({"entry": []})
    assert result is None


check("Text payload normalizes correctly", test_normalize_text)
check("Audio payload normalizes correctly", test_normalize_audio)
check("Status update returns None", test_normalize_status_update)
check("Malformed payload returns None", test_normalize_malformed)

print("\n=== 5. NormalizedMessage round-trip ===")


def test_round_trip():
    msg = NormalizedMessage(
        sender="2348001234567",
        message_id="wamid.xyz",
        timestamp=1700000000,
        message_type="text",
        body="Round trip test",
        media_id=None,
    )
    d = msg.to_dict()
    restored = NormalizedMessage.from_dict(d)
    assert msg == restored, f"Round trip failed: {msg} != {restored}"


def test_round_trip_audio():
    msg = NormalizedMessage(
        sender="2348009999999",
        message_id="wamid.audio",
        timestamp=1700000001,
        message_type="audio",
        body=None,
        media_id="media_123",
    )
    d = msg.to_dict()
    restored = NormalizedMessage.from_dict(d)
    assert msg == restored, f"Round trip failed: {msg} != {restored}"


check("NormalizedMessage text round-trip", test_round_trip)
check("NormalizedMessage audio round-trip", test_round_trip_audio)

print("\n" + "=" * 50)
print(f"Results: {len(passed)} passed, {len(errors)} failed")
if errors:
    print("\nFailed tests:")
    for name, err in errors:
        print(f"  - {name}: {err}")
    sys.exit(1)
else:
    print("\n✅ All checkpoint tests passed!")
    sys.exit(0)
