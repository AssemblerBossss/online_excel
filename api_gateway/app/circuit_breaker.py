from datetime import timedelta
from aiobreaker import CircuitBreaker
from enum import Enum
import logging

from api_gateway.app.config import settings

logger = logging.getLogger(__name__)


class ServiceName(str, Enum):
    AUTH = "auth"
    MAIN = "main"


_URL_TO_SERVICE: dict[str, ServiceName] = {
    settings.AUTH_SERVICE_URL: ServiceName.AUTH,
    settings.MAIN_SERVICE_URL: ServiceName.MAIN,
}


def resolve_service(target_url: str) -> ServiceName:
    """Определить ServiceName по base URL сервиса."""
    return _URL_TO_SERVICE.get(target_url, ServiceName.MAIN)


class CircuitBreakerRegistry:
    def __init__(self):
        self._breakers: dict[ServiceName, CircuitBreaker] = {}

    def get_breaker(self, service_name: ServiceName) -> CircuitBreaker:
        if service_name not in self._breakers:
            # Настройки под разные сервисы
            if service_name == ServiceName.AUTH:
                self._breakers[service_name] = CircuitBreaker(
                    fail_max=5,
                    timeout_duration=timedelta(seconds=60),
                    name=f"{service_name.value}_breaker",
                )
            else:
                self._breakers[service_name] = CircuitBreaker(
                    fail_max=3,
                    timeout_duration=timedelta(seconds=30),
                    name=f"{service_name.value}_breaker",
                )

        return self._breakers[service_name]

    def get_status(self) -> dict:
        (
            """Получить статус всех breaker'ов для мониторинга."""
            """
        Получить статус всех breaker'ов для мониторинга

        Доступные атрибуты CircuitBreaker:
        - state: текущее состояние (объект)
        - current_state: Enum состояния ('closed', 'open', 'half-open')
        - fail_counter: счетчик ошибок
        - fail_max: максимум ошибок до открытия
        - timeout_duration: таймаут до закрытия
        - opens_at: когда откроется (если открыт)
        - time_until_open: время до открытия
        """
        )
        status = {}

        for service, breaker in self._breakers.items():
            opened_at = breaker._state_storage.opened_at

            # current_state может быть объектом класса, а не Enum — берём имя явно
            state_raw = breaker.current_state
            if hasattr(state_raw, "value"):
                state_str = str(state_raw.value)
            elif hasattr(state_raw, "__name__"):
                state_str = state_raw.__name__  # ABCMeta случай
            else:
                state_str = str(state_raw)

            breaker_info: dict[str, str | int | None] = {
                "name": str(breaker.name) if breaker.name else None,
                "state": state_str,
                "fail_counter": int(breaker.fail_counter),
                "fail_max": int(breaker.fail_max),
                "timeout_duration_seconds": int(
                    breaker.timeout_duration.total_seconds()
                ),
                "opens_at": (
                    (opened_at + breaker.timeout_duration).isoformat()
                    if opened_at is not None
                    else None
                ),
            }

            status[str(service.value)] = breaker_info

        return status

    def reset_breaker(self, service: ServiceName) -> bool:
        """Принудительно сбросить Circuit Breaker для сервиса"""
        if service in self._breakers:
            self._breakers[service].close()
            logger.info(f"Circuit breaker for {service.value} manually reset")
            return True
        return False

    def get_breaker_info(self, service: ServiceName) -> dict | None:
        """Получить информацию о конкретном брекере"""
        if service not in self._breakers:
            return None

        breaker = self._breakers[service]
        return {
            "state": breaker.current_state.value,
            "fail_counter": breaker.fail_counter,
            "fail_max": breaker.fail_max,
            "timeout_duration": str(breaker.timeout_duration),
            "opens_at": breaker.opens_at.isoformat() if breaker.opens_at else None,
            "time_until_open": str(breaker.time_until_open)
            if breaker.time_until_open
            else None,
        }


circuit_breaker_registry = CircuitBreakerRegistry()
