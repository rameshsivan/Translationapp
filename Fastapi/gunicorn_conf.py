
from multiprocessing import cpu_count
import logging

bind = "0.0.0.0:8001"

workers = cpu_count() + 1
worker_class = 'uvicorn.workers.UvicornWorker'

loglevel = 'debug'
# accesslog = '/var/log/fastapi/access_log'
errorlog =  '/var/log/fastapi/error_log'

timeout = 60
# Set up logging
logger = logging.getLogger('uvicorn.access')
# 
handler = logging.FileHandler('/var/log/fastapi/access_log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')


handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

threads = 2
 