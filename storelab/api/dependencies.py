"""Dependency injection boundary for the cached simulation world."""

from typing import Annotated

from fastapi import Depends

from ..world import World, get_world

WorldDep = Annotated[World, Depends(get_world)]
