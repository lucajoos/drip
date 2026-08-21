"""Base entity for Drip."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import DripCoordinator


class DripEntity(CoordinatorEntity[DripCoordinator]):
    """Coordinator entity attached to the Drip device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DripCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
