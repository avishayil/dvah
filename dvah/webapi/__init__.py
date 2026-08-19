"""DVAH web API — a FastAPI layer over the harness for the browser lab UI.

Reuses ``dvah`` in-process (loader, trace/render, mutation engine, model adapters).
The only endpoint that exposes reference-solution content is ``/solution`` (explicit
reveal). User-edited code runs only through the sandboxed runner.
"""
