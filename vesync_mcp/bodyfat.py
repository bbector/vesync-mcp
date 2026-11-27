"""Optional body-fat ESTIMATE.

The ``/cloud/`` health endpoint returns raw bioimpedance but not the body-fat
percentage the app computes on-device (that uses a proprietary formula). This
module offers a rough estimate using the validated Deurenberg equation
(body fat % from BMI, age and sex) so you get a ballpark figure. It will not
match the scale exactly and ignores the impedance reading.

Gender mapping: VeSync stores gender as a string. Here ``"2"`` is treated as
male and anything else as female — this matches the test account used to build
the tool, but **verify it against your own profile** and adjust if needed.
"""
from __future__ import annotations


def estimate_body_fat(weight_kg, height_cm, age, gender) -> float | None:
    """Deurenberg (1991) body-fat % estimate. Returns None if inputs are missing."""
    if not weight_kg or not height_cm:
        return None
    bmi = weight_kg / (height_cm / 100) ** 2
    sex = 1 if str(gender) == "2" else 0  # 1 = male, 0 = female
    bf = 1.20 * bmi + 0.23 * (age or 0) - 10.8 * sex - 5.4
    return round(max(3.0, min(60.0, bf)), 1)
