import os
import json
import tempfile
import shutil

from navigation.common.params.params import Params


class TestParams:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        real_params_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'params.json')
        self.temp_params_path = os.path.join(tempfile.gettempdir(), 'params.json')
        shutil.copy(real_params_path, self.temp_params_path)
        self.params = Params()
        self.params.storage_file = self.temp_params_path
        self.params.load()

    def teardown_method(self):
        os.remove(self.temp_params_path)
        self.temp_dir.cleanup()

    def test_init_default_file(self):
        assert self.params.storage_file == os.path.join(tempfile.gettempdir(), 'params.json')

    def test_save(self):
        self.params.data = {"key": "value"}
        self.params.save()
        with open(self.params.storage_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == {"key": "value"}

    def test_get_existing_key(self):
        self.params.data = {"key": "value"}
        assert self.params.get("key") == "value"

    def test_get_nonexistent_key(self):
        assert self.params.get("nonexistent") is None

    def test_get_with_bytes_encoding(self):
        test_bytes = b"test bytes"
        self.params.put("key", test_bytes)
        result = self.params.get("key", encoding='bytes')
        assert result == test_bytes

    def test_get_mapbox_token_utf8(self):
        result = self.params.get_mapbox_token()
        assert isinstance(result, str) and len(result) > 0

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
        assert self.params.data["key"] == str("value")

    def test_put_bytes(self):
        test_bytes = b"test bytes"
        self.params.put("key", test_bytes)
        result = self.params.get("key", encoding='bytes')
        assert result == test_bytes

    def test_put_mapbox_token_string(self):
        test_token = "test_token"
        self.params.put("MapboxToken", test_token)
        result = self.params.get_mapbox_token()
        assert isinstance(result, str) and len(result) > 0

    def test_put_other_types(self):
        self.params.put("int_key", 42)
        assert self.params.data["int_key"] == 42
        self.params.put("list_key", [1, 2, 3])
        assert self.params.data["list_key"] == [1, 2, 3]
