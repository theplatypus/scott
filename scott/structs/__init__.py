"""Retro-compatibility shim: exposes scott.structs.{graph,node,edge}."""

from . import graph, node, edge

__all__ = ["graph", "node", "edge"]
