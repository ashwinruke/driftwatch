"""Langfuse tracing (spec §25), fully optional: if LANGFUSE_PUBLIC_KEY
isn't set, traced_generation/traced_span return the original function
completely untouched -- not even a no-op wrapper -- so there's zero
overhead and zero risk to the review pipeline when tracing isn't
configured. LANGFUSE_SECRET_KEY/LANGFUSE_BASE_URL aren't read by this
module at all; the Langfuse SDK reads those itself from the environment
when get_client() is first called.

Spec's target layout has separate observability/langfuse.py and
observability/tracing.py; collapsed to this one file since all the logic
here is Langfuse-specific anyway -- splitting one cohesive concern across
two files would be artificial."""

from driftwatch.app import config

ENABLED = bool(config.LANGFUSE_PUBLIC_KEY)

if ENABLED:
    from langfuse import get_client, observe
else:
    get_client = None
    observe = None


def traced_generation(name: str):
    """Wraps an LLM call (e.g. GeminiProvider.generate_findings,
    draft_update) as a Langfuse "generation" span."""

    def decorator(func):
        if not ENABLED:
            return func
        return observe(as_type="generation", name=name)(func)

    return decorator


def traced_span(name: str):
    """Wraps a top-level review-run entry point (review_pull_request,
    _handle_pr_merged) as a Langfuse span. A span with no parent starts a
    new trace -- this is the "review run" spec §25 asks to be tracked."""

    def decorator(func):
        if not ENABLED:
            return func
        return observe(as_type="span", name=name)(func)

    return decorator


def tag_current_run(**metadata):
    """Attaches identifying metadata (repository, pull_request, ...) to
    the currently active span/trace. A no-op if tracing isn't enabled."""
    if not ENABLED:
        return
    get_client().update_current_span(metadata=metadata)
