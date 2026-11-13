"""
Portfolio: the services that compute what a user's portfolio is and did.

- ``portfolio_service``: ``PortfolioService`` (summary, history, positions, report) and the WAC cost basis.
- ``lots_analysis_service``: ``LotsAnalysisService`` and ``get_lots_analysis`` (the lots behind a position).

The math itself is in ``services/financial_math/``; these services read the data, call it and shape the answer.
"""
