from datetime import datetime
# from requests import exceptions
# from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# # Define a retry decorator for asynchronous functions
# async_retry = retry(
#     stop=stop_after_attempt(3),
#     wait=wait_exponential(multiplier=1, min=4, max=60),
#     retry=retry_if_exception_type((exceptions.ConnectionError, exceptions.ReadTimeout, exceptions.RequestException, exceptions.Timeout, exceptions.ConnectTimeout)),
#     reraise=True
# )


def get_time_formatted():
    time = datetime.utcnow()

    return {"year": time.year, "month": time.month, "day": time.day, "hour": time.hour, "min": time.minute}
