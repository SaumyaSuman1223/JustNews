"""FINDING (Yu et al., CIKM '23) over JustNews's frozen multilingual vectors:
the user tower, the simulated-federated trainer with fine-grained
interpolation and dynamic clustering, and the metrics everything is judged
by. Offline only - apps/ never imports this (CLAUDE.md); only the exported
ONNX file and the vectors it writes cross that line.

Training runs over *simulated* clients replayed from logs. Serving is
centralised. This is not a federated production system.
"""
