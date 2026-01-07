import pytest
from hiero_sdk_python import PrivateKey, PublicKey

from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)


class TestResolveKey:
    """Unit tests for HederaParameterNormaliser.resolve_key method."""

    def test_returns_none_when_raw_value_is_none(self):
        """Should return None when raw_value is None."""
        user_key = PrivateKey.generate_ed25519().public_key()
        result = HederaParameterNormaliser.resolve_key(None, user_key)
        assert result is None

    def test_returns_none_when_raw_value_is_false(self):
        """Should return None when raw_value is False."""
        user_key = PrivateKey.generate_ed25519().public_key()
        result = HederaParameterNormaliser.resolve_key(False, user_key)
        assert result is None

    def test_returns_user_key_when_raw_value_is_true(self):
        """Should return user_key when raw_value is True."""
        user_key = PrivateKey.generate_ed25519().public_key()
        result = HederaParameterNormaliser.resolve_key(True, user_key)
        assert result is not None
        assert isinstance(result, PublicKey)
        assert result.to_string_der() == user_key.to_string_der()

    def test_parses_der_encoded_ed25519_public_key_string(self):
        """Should parse a DER-encoded Ed25519 public key string."""
        custom_keypair = PrivateKey.generate_ed25519()
        custom_public_key_str = custom_keypair.public_key().to_string_der()
        user_key = PrivateKey.generate_ed25519().public_key()

        result = HederaParameterNormaliser.resolve_key(custom_public_key_str, user_key)

        assert result is not None
        assert isinstance(result, PublicKey)
        assert result.to_string_der() == custom_public_key_str

    def test_parses_raw_ed25519_public_key_string(self):
        """Should parse a raw Ed25519 public key string (hex format)."""
        custom_keypair = PrivateKey.generate_ed25519()
        custom_public_key_str = custom_keypair.public_key().to_string_raw()
        user_key = PrivateKey.generate_ed25519().public_key()

        result = HederaParameterNormaliser.resolve_key(custom_public_key_str, user_key)

        assert result is not None
        assert isinstance(result, PublicKey)
        assert result.to_string_raw() == custom_public_key_str

    def test_parses_der_encoded_ecdsa_public_key_string(self):
        """Should parse a DER-encoded ECDSA public key string."""
        custom_keypair = PrivateKey.generate_ecdsa()
        custom_public_key_str = custom_keypair.public_key().to_string_der()
        user_key = PrivateKey.generate_ed25519().public_key()

        result = HederaParameterNormaliser.resolve_key(custom_public_key_str, user_key)

        assert result is not None
        assert isinstance(result, PublicKey)
        assert result.to_string_der() == custom_public_key_str

    def test_parses_raw_ecdsa_public_key_string(self):
        """Should parse a raw ECDSA public key string (hex format)."""
        custom_keypair = PrivateKey.generate_ecdsa()
        custom_public_key_str = custom_keypair.public_key().to_string_raw()
        user_key = PrivateKey.generate_ed25519().public_key()

        result = HederaParameterNormaliser.resolve_key(custom_public_key_str, user_key)

        assert result is not None
        assert isinstance(result, PublicKey)
        assert result.to_string_raw() == custom_public_key_str

    def test_raises_error_for_invalid_key_string(self):
        """Should raise an error when provided an invalid key string."""
        user_key = PrivateKey.generate_ed25519().public_key()
        invalid_key_string = "invalid_key_string_12345"

        with pytest.raises(Exception):
            HederaParameterNormaliser.resolve_key(invalid_key_string, user_key)

    def test_raises_error_for_empty_key_string(self):
        """Should raise an error when provided an empty key string."""
        user_key = PrivateKey.generate_ed25519().public_key()

        with pytest.raises(Exception):
            HederaParameterNormaliser.resolve_key("", user_key)
