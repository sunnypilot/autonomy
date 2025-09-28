import base64
import os
import json
import tempfile
from navigation.common.params.params import Params


class TestParams:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.params_file = os.path.join(self.temp_dir.name, 'params.json')
        self.params = Params(self.params_file)

    def teardown_method(self):
        self.temp_dir.cleanup()

    def test_init_default_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            params_file = os.path.join(temp_dir, 'params.json')
            params = Params(params_file)
            assert params.storage_file == params_file
            assert params.data == {}

    def test_init_custom_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_file = os.path.join(temp_dir, 'custom.json')
            params = Params(custom_file)
            assert params.storage_file == custom_file

    def test_load_existing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            params_file = os.path.join(temp_dir, 'params.json')
            test_data = {"key1": "value1", "key2": 42}
            with open(params_file, 'w') as f:
                json.dump(test_data, f)
            params = Params(params_file)
            assert params.data == test_data

    def test_load_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            params_file = os.path.join(temp_dir, 'nonexistent.json')
            params = Params(params_file)
            assert params.data == {}

    def test_load_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            params_file = os.path.join(temp_dir, 'invalid.json')
            with open(params_file, 'w') as f:
                f.write("invalid json")
            params = Params(params_file)
            assert params.data == {}

    def test_save(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            params_file = os.path.join(temp_dir, 'params.json')
            params = Params(params_file)
            params.data = {"key": "value"}
            params.save()
            with open(params_file, 'r') as f:
                saved_data = json.load(f)
            assert saved_data == {"key": "value"}

    def test_get_existing_key(self):
        self.params.data = {"key": "value"}
        assert self.params.get("key") == "value"

    def test_get_nonexistent_key(self):
        assert self.params.get("nonexistent") is None

    def test_get_with_bytes_encoding(self):
        test_bytes = b"test bytes"
        encoded = base64.b64encode(test_bytes).decode('utf-8')
        self.params.data = {"key": encoded}
        result = self.params.get("key", encoding='bytes')
        assert result == test_bytes

    def test_get_mapbox_token_utf8(self):
        test_token = "test_token"
        encoded = base64.b64encode(test_token.encode('utf-8')).decode('utf-8')
        self.params.data = {"MapboxToken": encoded}
        result = self.params.get("MapboxToken", encoding='utf8')
        assert result == test_token

    def test_get_other_key_utf8(self):
        self.params.data = {"other_key": "plain_value"}
        result = self.params.get("other_key", encoding='utf8')
        assert result == "plain_value"

    def test_get_int_valid(self):
        self.params.data = {"key": "42"}
        assert self.params.get_int("key") == 42

    def test_get_int_invalid(self):
        self.params.data = {"key": "not_a_number"}
        assert self.params.get_int("key") == 0

    def test_get_int_none(self):
        assert self.params.get_int("nonexistent") == 0

    def test_put_string(self):
        self.params.put("key", "value")
        assert self.params.data["key"] == "value"

    def test_put_bytes(self):
        test_bytes = b"test bytes"
        self.params.put("key", test_bytes)
        expected = base64.b64encode(test_bytes).decode('utf-8')
        assert self.params.data["key"] == expected

    def test_put_mapbox_token_string(self):
        test_token = "test_token"
        self.params.put("MapboxToken", test_token)
        expected = base64.b64encode(test_token.encode('utf-8')).decode('utf-8')
        assert self.params.data["MapboxToken"] == expected

    def test_put_other_types(self):
        self.params.put("int_key", 42)
        assert self.params.data["int_key"] == 42
        self.params.put("list_key", [1, 2, 3])
        assert self.params.data["list_key"] == [1, 2, 3]
