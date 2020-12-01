import time
import json
import os

import click
import requests
import requests_html

BS_API_KEY = os.getenv('BS_API_KEY')
BS_SITE_KEY = os.getenv('BS_SITE_KEY')
BS_SECURITY_TOKEN = os.getenv('BS_SECURITY_TOKEN')

session = requests_html.HTMLSession()


@click.command()
def bs():
    """Burning series command line downloder"""

    if not BS_API_KEY or not BS_SITE_KEY:
        click.echo('No api or site key found')
        quit()

    series = get_series()
    seasons = get_seasons(series)
    episodes = get_episodes(seasons)

    confirm = 'Do you really want to download {0} season(s) with {1} episode(s)'
    click.confirm(confirm.format(len(seasons), sum(len(e) for e in episodes)), abort=True)

    # pathlib here...
    file = f'{series.split("/")[-2]}.txt'

    for season in episodes:
        with click.progressbar(season, label='Decoding captchas') as bar:
            for episode in bar:
                # file.write(decaptcha(episode) + '\n')
                print(episode)
                print('\n')


def get_series():
    """Get wanted series"""

    all_series = get_all_series()
    series = []

    while True:
        prompt = click.prompt('Enter series')
        wanted = {name: url for name, url in all_series.items() if prompt.lower() in name.lower()}

        if wanted:
            break

    # select by number
    for i, name in enumerate(wanted):
        click.echo('[{0}]: {1}'.format(i + 1, name))
        series.append(name)

    i = click.prompt('Select series', type=int) - 1 if len(wanted) > 1 else 0

    return wanted[series[i]]


def get_seasons(series):
    """Get selected series"""

    all_seasons = get_all_seasons(series)
    seasons = {}

    # if len(all_seasons) > 1:
    sel = click.prompt('Select season(s)', default='{0}-{1}'.format([*all_seasons][0], [*all_seasons][-1]))

    # e.g. 1 2 3 or 1-3
    for s in sel.split():
        i = s.split('/')[-1]

        if '-' in s:
            start, stop = [int(i) for i in s.split('-')]

            for i in range(start, stop + 1):
                seasons[int(i)] = f'https://bs.to/{all_seasons[int(i)]}'

        else:
            seasons[int(i)] = f'https://bs.to/{all_seasons[int(i)]}'

    return list(seasons.values())


def get_episodes(seasons):
    """Get all season episodes as list"""

    return [get_all_episodes(s) for s in seasons]


def get_all_series():
    """Get all series as dictionary"""

    series = bsto('https://bs.to/andere-serien', '.genre li a')

    return {s.text: f'https://bs.to/{s.attrs["href"]}/de/' for s in series}


def get_all_seasons(series):
    """Get all seasons as dictionary"""

    seasons = bsto(series, '#seasons li a')

    return {int(s.attrs['href'].split('/')[-2]): s.attrs['href'] for s in seasons}


def get_all_episodes(season):
    """Get episodes of season as list"""

    rows = bsto(season, '.episodes tr')
    episodes = []

    with click.progressbar(rows, label='Collecting episodes') as bar:
        for _, e in enumerate(bar):
            hoster = e.find('td')[-1].find('a')

            hosts = []

            for h in hoster:
                lid = bsto(f'https://bs.to/{h.attrs["href"]}', '.hoster-player')[0]
                hosts.append(lid.attrs['data-lid'])

            if hosts:
                episodes.append(hosts)

    return episodes


def decaptcha(urls):
    """Solve captcha"""

    def create_task(url):
        return requests.post("https://api.anti-captcha.com/createTask", data=json.dumps({
            "clientKey": BS_API_KEY,
            "task": {
                "type": "NoCaptchaTaskProxyless",
                "websiteKey": BS_SITE_KEY,
                "websiteURL": url
            }
        }))

    def get_task_result(task):
        return requests.post("https://api.anti-captcha.com/getTaskResult", data=json.dumps({
            "clientKey": BS_API_KEY,
            "taskId": task.json()['taskId']
        }))

    for url in urls:
        captcha = create_task(url)

        # average time to solve captcha
        time.sleep(15)

        # try up to 90 more secs
        for attempt in range(90):
            result = get_task_result(captcha).json()

            if 'status' in result:

                if 'processing' in result['status']:
                    time.sleep(1)
                    continue

                if 'ready' in result['status']:
                    return requests.post('https://bs.to/ajax/embed.php', params={
                        'token': BS_SECURITY_TOKEN,
                        'LID': '',
                        'ticket': result['solution']['gRecaptchaResponse'],
                    })

            if 'errorCode' in result:
                click.echo('Error #{errorId}: {#errorCode}'.format(**result))
                click.echo('{errorDescription}'.format(**result))
                quit()


def bsto(url, sel):
    """Get a selector from url"""

    return session.get(url).html.find(sel)


if __name__ == '__main__':
    bs()
