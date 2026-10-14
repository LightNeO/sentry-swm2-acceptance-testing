"""OTA commands that do not actually flash anything: version/format validation (OTA-5, OTA-11, OTA-12)."""

import pytest

pytestmark = [pytest.mark.functional, pytest.mark.ota]


@pytest.mark.tc("TC-OTA-07")
@pytest.mark.parametrize("version", ["2.1", "2.1.0.0", "a.b.c", "2.1.x", "-1.0.0"])
def test_install_bad_version_format_gives_e414(dut, version):
    r = dut.exchange(f"ota install {version}", idle=1.5, timeout=8)
    assert r.has_code("E414"), f"'{version}': expected E414, got {r.codes}\n{r}"
    assert r.has("Format: X.Y.Z")


@pytest.mark.tc("TC-OTA-08")
@pytest.mark.parametrize("version", ["9.9.9", "2.2.0"])
def test_install_unknown_version_gives_e415(dut, version):
    r = dut.exchange(f"ota install {version}", until=r"E41[45]", timeout=15)
    assert r.has_code("E415"), f"'{version}': expected E415, got {r.codes}\n{r}"
    assert r.has(f"v{version} not found on server")


@pytest.mark.tc("TC-OTA-29")
@pytest.mark.parametrize("url", ["ftp://x", "x", "file:///x"])
def test_url_scheme_must_be_http_or_https(dut, url):
    r = dut.exchange(f"ota url {url}")
    assert r.has_code("E418"), f"'{url}': expected E418, got {r.codes}\n{r}"
    assert r.has("must start with http:// or https://")


@pytest.mark.tc("TC-OTA-29")
def test_url_without_argument_gives_usage_error(dut):
    """An empty url is a missing-argument case (E400), not a bad-scheme case (E418)."""
    r = dut.exchange("ota url")
    assert r.has_code("E400"), f"expected E400, got {r.codes}\n{r}"


@pytest.mark.tc("TC-OTA-31")
def test_server_shows_github_by_default(dut):
    r = dut.exchange("ota server")
    assert r.has("raw.githubusercontent.com") and r.has("(default)"), r


@pytest.mark.tc("TC-WF-15")
def test_net_shows_ip_gateway_dns_mac(dut):
    r = dut.exchange("net")
    assert r.search(r"ip:\s+\d+\.\d+\.\d+\.\d+")
    assert r.search(r"gateway:\s+\d+\.\d+\.\d+\.\d+")
    assert r.search(r"mac:\s+[0-9a-f:]{17}")
