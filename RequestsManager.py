from random import random,randint
import httpx

UserAgents = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246",
              "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36",
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9",
              "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
              "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1"]
class RequestsManager:

    def __init__ (self,user_agents: list):
        """
        The __init__ function is called when the class is instantiated.
        It sets up the user_agents list and error_requests list as attributes of the class.
        The user_agents attribute will be a list of strings that are used to set headers for requests.
        """

        self.user_agents = user_agents
        self.error_requests = []
    async def get_page(self, client, url, limiter, max_retries=10):
        """
        The get_page function is responsible for requesting html based on imputed url
        if connection fail number of retries tries multiple times."""

        retries = 0
        while retries < max_retries:
            try:
                async with limiter:
                    us_ag_index = randint(0, len(self.user_agents) - 1)
                    headers = {"User-Agent": self.user_agents[us_ag_index]}
                    resp = await client.get(url,headers=headers)
                    html_text = resp.text  # converts the request output to text
                    return html_text
            except (httpx.ReadTimeout,
                    httpx.ReadError,
                    httpx.ConnectTimeout,
                    httpx.PoolTimeout,
                    httpx.RemoteProtocolError):
                if retries == 10:
                    self.error_requests.append(url)
                else:
                    retries += 1
            except httpx.ConnectError:
                continue
        return self.error_requests.append(url)
