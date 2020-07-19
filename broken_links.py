#!/usr/bin/env python3
import aiohttp, asyncio, argparse, re, sys
from bs4 import BeautifulSoup

class BrokenLinks():
    def __init__(self, domain):
        self.domain = domain
        self.protocol = None
        self.full_url = self.domain
        self.links = []
        self.proccessed = []
        self.bad_links = []
        self.urls_patterns  = {
            'url_validation': r'',
            'internal_link': r'',
            'http|https': r'^(https|http)://',
            'first_slash': r'([^/]+)'
            }

    async def proccess(self, url):
        self.urls_patterns['base_domain'] = r'^(http|https)://.*{}.*$'.format(self.domain.lower())
        await self.get_session()
        self.links = await self.filtering(url)
        switch = True
        while switch:
            for a in list(set(self.links)):
                if a not in self.proccessed:
                    print("Loading url: ", a)
                    code = await self.fetch(a, format='status_code')
                    self.proccessed.append(a)
                if bool(re.match(self.urls_patterns["base_domain"], a)):
                    l = await self.filtering(a)
                    self.links += l
            switch = False
        await self.session.close()
        if len(list(set(self.bad_links))) == 0:
            print("No broken links was found")
        else:
            print("Found {0} broken links: {1}".format(len(self.bad_links), self.bad_links))

    async def filtering(self, url):
        l = await self.extract_links(url)
        f = [self.full_url + i for i in l if not bool(re.match(self.urls_patterns["http|https"], i))]
        return list(set([a for a in l if bool(re.match(self.urls_patterns["http|https"], a)) and a not in self.proccessed])) + [a for a in f if a not in self.proccessed]

    async def get_session(self):
        self.session = aiohttp.ClientSession()

    async def fetch(self, url, format='text'):
        try:
            async with self.session.get(url) as response:
                if format == 'text':
                    return await response.text()
                elif format == 'status_code':
                    if response.status not in [200]:
                        self.bad_links.append(url)
                        print()
                        print("----------- Bad link found: {0}, status code: {1}".format(url, response.status))
                        print()
                    return response.status
        except Exception as e:
            print("Failed to fetch url: ", e)

    async def make_soup(self, html):
        return BeautifulSoup(html,'html.parser')

    async def extract_links(self, url):
        html = await self.fetch(url, format='text')
        l = []
        if not html:
            return []
        soup = await self.make_soup(html)
        s = soup.find_all("a")
        for a in s:
            try:
                l.append(a['href'])
            except Exception as e:
                pass
        return l

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--domain', help="domain to scan. Ex. 'http://example.com'",  type=str, required=True)
    args = parser.parse_args()
    b = BrokenLinks(args.domain)
    protocol = re.search(b.urls_patterns["http|https"], args.domain)
    if protocol:
        if protocol.group(1):
            b.protocol = protocol
            b.domain = re.search(b.urls_patterns["first_slash"],b.domain[len(protocol.group(1))+3:]).group(1)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(b.proccess(args.domain))
