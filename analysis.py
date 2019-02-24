from datetime import datetime, timedelta
from urllib.parse import quote_plus
import click
import math
from InstagramAPI import InstagramAPI

class PrintableDateTime():
    def __init__(self, epoch_time):
        self.date_time = ticks_to_datetime(epoch_time)

    def __repr__(self):
        return self.date_time.strftime("%Y-%m-%d %H:%M:%S")


def ticks_to_datetime(epoch_time):
    return datetime.utcfromtimestamp(epoch_time)


def setup_api(username, password):
    api = InstagramAPI(username, password)
    api.login()
    return api


def get_tag_data(api, tag):
    print(tag)
    api.tagFeed(quote_plus(tag))
    top_posts = [] if api is None or api.LastJson is None else [{"likes": item.get('like_count', None),
                                                                 "views": item.get('view_count', None),
                                                                 "caption": (item['caption'].get('text', None) if item.get('caption', None) is not None else None),
                                                                 "id": item['id'],
                                                                 "comments": item.get(
        'comment_count', None),
        "date_time": PrintableDateTime(item.get("taken_at", None))} for item in api.LastJson.get('ranked_items', [])]

    api.searchTags(quote_plus(tag))
    tag_post_count = 0 if api.LastJson is None or api.LastJson['results'] is None or len(
        api.LastJson['results']) <= 0 else api.LastJson['results'][0]['media_count']

    return {"tag": tag, "data": {"post_count": tag_post_count, "top_posts": top_posts}}


def engagement_calculations(tag_data):
    user_amount = tag_data.get('post_count', 0)

    num_top_posts = len(tag_data.get('top_posts', None))

    avg_likes = sum([item['likes']
                     for item in tag_data['top_posts'] if item['likes'] is not None]) / num_top_posts if num_top_posts > 0 else 0

    view_counts = [item['views']
                   for item in tag_data['top_posts'] if item['views'] is not None]
    avg_views = int(sum(view_counts) / len(view_counts)
                    ) if len(view_counts) > 0 else 0

    avg_comments = sum([item['comments']
                        for item in tag_data['top_posts'] if item['comments'] is not None]) / num_top_posts if num_top_posts > 0 else 0

    likes_per_min = sum([item['likes'] / math.floor(((datetime.utcnow(
    ) - item['date_time'].date_time).total_seconds() / 60)) for item in tag_data['top_posts'] if item['likes'] is not None and item['date_time'] is not None]) / num_top_posts if num_top_posts > 0 else 0

    views_per_min = sum([item['views'] / math.floor(((datetime.utcnow() - item['date_time'].date_time).total_seconds() / 60))
                         for item in tag_data['top_posts'] if item['views'] is not None and item['date_time'] is not None]) / len(view_counts) if len(view_counts) > 0 else 0

    engagement_per_min = sum([(item['views'] / 10 if item['views'] and item['views'] / 10 > item['likes'] else item['likes'])/ math.floor(((datetime.utcnow(
    ) - item['date_time'].date_time).total_seconds() / 60)) for item in tag_data['top_posts'] if item['likes'] is not None and item['date_time'] is not None]) / num_top_posts if num_top_posts > 0 else 0

    like_engagement = user_amount / avg_likes if avg_likes > 0 else 0

    views_engagement = user_amount / avg_views if avg_views > 0 else 0

    return {
        "user_amount": user_amount,
        "avg_likes": avg_likes,
        "avg_views": avg_views,
        "avg_comments": avg_comments,
        "likes_per_min": likes_per_min,
        "views_per_min": views_per_min,
        "like_engagement": like_engagement,
        "views_engagement": views_engagement,
        "engagement_per_min": engagement_per_min
    }


def get_hash_tags(file):
    tags = []
    with open(file, "r") as f:
        tags = [line.replace("#", "").strip() for line in f.readlines()]
    return tags


def rank_hash_tags(api, tags):
    tag_datas = [get_tag_data(api, tag) for tag in tags]
    all_engage_calcs = {item['tag']: engagement_calculations(
        item['data']) for item in tag_datas}

    rank_list = [el[0] for el in sorted(all_engage_calcs.items(), key=lambda x: (
        x[1]['engagement_per_min'], x[1]['user_amount']))]

    return all_engage_calcs, rank_list

def generate_output(ranked_list, all_engage_calcs):
    lines = ["Hashtag,Engagement/min,user_amount,avg likes,avg views,avg comments"]
    for tag in ranked_list:
        calcs = all_engage_calcs[tag]
        line = f'{tag},{calcs["engagement_per_min"]},{calcs["user_amount"]},{calcs["avg_likes"]},{calcs["avg_views"]},{calcs["avg_comments"]}'
        lines.append(line)
    return lines

def write_results(results, out_file):
    with open(out_file, "w") as f:
        for result in results:
            f.write(result + "\n")

@click.command()
@click.option('-u', '--username', required=True, type=str, help='Instagram Username')
@click.option('-p', '--password', required=True, type=str, help='Instagram Password')
@click.option('-f', '--hashtags-path', required=True, type=str, help='Path to hashtags intake')
@click.option('-o', '--out-path', default='ranked_list.csv', type=str, help='File path for out file (should be .csv)')
def run(username, password, hashtags_path, out_path):
    api = setup_api(username, password)
    tags = get_hash_tags(hashtags_path)
    all_engage_calcs, ranked_list = rank_hash_tags(api, tags)

    write_results(generate_output(ranked_list, all_engage_calcs), out_path)

if __name__ == "__main__":
    run()
