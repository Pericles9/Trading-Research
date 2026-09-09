"""Ridge-first feature detection on the scale field.

Built from claude/field_feature_extraction_methods.md. Parameters are frozen in
config/scale_field_detector.json, committed before the first run that uses them.

SCOPE. This is an instrument. It produces a feature table -- location, selected scale,
fitted duration, tilt, persistence, significance -- and it touches no forward return.
D22 closed the scale-space field as a detector; building this reopens that on Cooper's
instruction of 2026-09-09 and does not disturb D24 or D25.

THE KAPPA GATE IS LIVE. detect() will refuse to run without an explicit noise constant and
an explicit kappa, because the Poisson constant 0.87 is wrong on this tape and the matched
null that should replace it is itself under retraction. Synthetic tapes only until that is
settled.
"""
from .moments import (  # noqa: F401
    CUT,
    POISSON_NOISE_CONSTANT,
    FieldPoint,
    F,
    F_t,
    F_tt,
    F_tu,
    F_u,
    F_uu,
    field_at,
    field_fft,
    lam_hat,
    moments,
    n_eff,
)
from .ridge import (  # noqa: F401
    Feature,
    apex_newton,
    detect,
    feature_rows,
    fit_duration,
    polish_scale,
    ridge_polish,
)
