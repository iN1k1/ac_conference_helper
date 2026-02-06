import signal
import time
from functools import wraps

import numpy as np
import structlog

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class TimeoutExpired(Exception):
    pass


def alarm_handler(signum, frame):
    raise TimeoutExpired


def timeout(timeout_duration=10, default_output=[]):
    """Decorator to run a function with timeout"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set alarm.
            signal.signal(signal.SIGALRM, alarm_handler)
            signal.alarm(timeout_duration)

            try:
                result = func(*args, **kwargs)
            except TimeoutExpired:
                logger.error("Function timeout occurred", function=func.__name__, timeout=timeout_duration)
                result = default_output

            # Cancel the alarm.
            signal.alarm(0)
            return result
        return wrapper
    return decorator


def run_with_timeout(func, args=(), kwargs={}, timeout_duration=10, default_output=[]):
    """Run func with given args and kwargs with timeout"""
    # Set alarm.
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(timeout_duration)

    try:
        result = func(*args, **kwargs)
    except TimeoutExpired:
        logger.error("Function timeout occurred", function=func.__name__, timeout=timeout_duration)
        result = default_output

    # Cancel the alarm.
    signal.alarm(0)
    return result


def int_list_to_str(ints: list[int]) -> str:
    output = ", ".join([str(item) for item in ints])
    if not output:
        output = "-"
    return output


def mean(values: list[int | float], prec: int = 2) -> str:
    if not values:
        return "-"

    mean_val = sum(values) / len(values)
    return f"{mean_val:.{prec}f}"


def std(values: list[int | float], prec: int = 2) -> str:
    if not values:
        return "-"

    std_val = np.std(values)
    return f"{std_val:.{prec}f}"


def wait_for_page_load(element_id: str, content_selector: str = ".note", timeout: int = 10, max_retries: int = 3):
    """Decorator to wait for page elements to load before executing function."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not SELENIUM_AVAILABLE:
                logger.warning("Selenium not available, skipping page load verification")
                return func(self, *args, **kwargs)
            
            for attempt in range(max_retries):
                try:
                    logger.info("Waiting for page load", element_id=element_id, content_selector=content_selector, attempt=attempt + 1)
                    
                    # Wait for main element to be present
                    wait = WebDriverWait(self.driver, timeout)
                    main_element = wait.until(
                        EC.presence_of_element_located((By.ID, element_id))
                    )
                    
                    # Wait for content to be loaded (re-find to avoid stale elements)
                    wait.until(
                        lambda driver: driver.find_element(By.ID, element_id).find_elements(By.CSS_SELECTOR, content_selector)
                    )
                    
                    logger.info("Page loaded successfully", element_id=element_id, attempt=attempt + 1)
                    break
                    
                except TimeoutException:
                    logger.warning("Timeout waiting for page to load", element_id=element_id, timeout=timeout, attempt=attempt + 1)
                    if attempt == max_retries - 1:
                        logger.error("Max retries reached for page load", element_id=element_id)
                        return []
                    time.sleep(1)  # Brief pause before retry
                except Exception as e:
                    logger.warning("Error waiting for page to load", element_id=element_id, error=str(e), attempt=attempt + 1)
                    if attempt == max_retries - 1:
                        logger.error("Max retries reached for page load", element_id=element_id, error=str(e))
                        return []
                    time.sleep(1)  # Brief pause before retry
            
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def wait_for_url_change(timeout: int = 10, poll_frequency: float = 0.5):
    """Wait for URL to change and page to be ready after navigation."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not SELENIUM_AVAILABLE:
                logger.warning("Selenium not available, skipping URL change verification")
                return func(self, *args, **kwargs)
            
            # Get current URL before navigation
            current_url = self.driver.current_url
            
            # Execute the function (should contain navigation)
            result = func(self, *args, **kwargs)
            
            try:
                logger.info("Waiting for URL change", from_url=current_url)
                
                # Wait for URL to change
                wait = WebDriverWait(self.driver, timeout)
                wait.until(
                    lambda driver: driver.current_url != current_url
                )
                
                # Wait for page to be ready (document.readyState)
                wait.until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                new_url = self.driver.current_url
                logger.info("URL changed successfully", from_url=current_url, to_url=new_url)
                
            except TimeoutException:
                logger.error("Timeout waiting for URL change", from_url=current_url, timeout=timeout)
            except Exception as e:
                logger.error("Error waiting for URL change", from_url=current_url, error=str(e))
            
            return result
        return wrapper
    return decorator


def navigate_and_wait(driver, url: str, timeout: int = 10, wait_for_elements: list = None):
    """Navigate to URL and wait for specific elements to be present.
    
    Args:
        driver: Selenium WebDriver instance
        url: URL to navigate to
        timeout: Maximum time to wait for elements
        wait_for_elements: List of tuples (By, selector) to wait for after navigation
    
    Returns:
        None
    """
    if not SELENIUM_AVAILABLE:
        logger.warning("Selenium not available, skipping navigation")
        return
    
    current_url = driver.current_url
    
    try:
        logger.info("Navigating to URL", from_url=current_url, to_url=url)
        driver.get(url)
        
        # Wait for URL to change
        wait = WebDriverWait(driver, timeout)
        wait.until(
            lambda d: d.current_url != current_url
        )
        
        # Wait for page to be ready
        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        new_url = driver.current_url
        logger.info("Navigation successful", from_url=current_url, to_url=new_url)
        
        # Wait for specific elements if provided
        if wait_for_elements:
            logger.info("Waiting for specific elements", elements=wait_for_elements)
            for selector_type, selector_value in wait_for_elements:
                try:
                    wait.until(EC.presence_of_element_located((selector_type, selector_value)))
                    logger.info("Element found", selector=selector_value)
                except TimeoutException:
                    logger.warning("Element not found after navigation", selector=selector_value)
                    # Continue trying other elements even if one fails
        
    except TimeoutException:
        logger.error("Timeout during navigation", from_url=current_url, to_url=url, timeout=timeout)
        raise
    except Exception as e:
        logger.error("Error during navigation", from_url=current_url, to_url=url, error=str(e))
        raise
