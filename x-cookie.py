import json
from pathlib import Path

import browser_cookie3


def cookie_http_only(c):
    return bool(getattr(c, "httponly", False) or c._rest.get("HttpOnly"))


def to_playwright_storage(cookies):
    out = {"cookies": [], "origins": []}
    for c in cookies:
        out["cookies"].append(
            {
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "expires": c.expires or -1,
                "httpOnly": cookie_http_only(c),
                "secure": bool(getattr(c, "secure", False)),
                "sameSite": "Lax",
            }
        )
    return out


cj = browser_cookie3.chrome(domain_name="x.com")  # use .brave(), .edge() if needed
storage = to_playwright_storage(cj)

out_path = Path("browser_profiles/x_session.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(storage, indent=2))
print(f"Saved {out_path}")
