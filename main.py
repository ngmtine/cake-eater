EMAIL = ""
PASSWORD = ""

import os
import requests
from bs4 import BeautifulSoup

def get_download_target_urls(serialization_id):
	""" 連載固有のID（serialization_id）から、ダウンロード対象のページURLを取得し、リストで返します """
	download_target_urls = []

	for page_num in range(1, 999):
		request_url = f"https://cakes.mu/series/posts_pager?page={page_num}&sort=&serialization_id={serialization_id}"
		response = requests.get(request_url)
		soup = BeautifulSoup(response.text,'lxml')
		pages = soup.select(".post-title-full a")

		if pages == []: # ページ遷移先がなくなった時
			break

		while pages:
			try:
				article = pages.pop()
				relative_url = article.get("href")
				url = f"https://cakes.mu{relative_url}"
				download_target_urls.append(url)
			except Exception as e:
				print(e)

	return download_target_urls

def download_images(article_url, series_num, cookie):
	"""個別ページのurlから画像をダウンロードします
	series_numは連載の中の何話目かを示す変数であるが、
	cakesは連載ごとにそのページが第何話なのか特定できるシリーズ番号を振っていない？のでこちらで管理する必要がある"""
	
	with open(downloaded_txt, mode="r") as f:
		downloaded_list = list(map(lambda i: i.rstrip(), f.readlines()))
		if article_url in downloaded_list:
			return
			
	response = requests.get(article_url, cookies=cookie)
	soup = BeautifulSoup(response.text,'lxml')

	author = soup.find("meta", attrs={"name": "author"})["content"] # 著者
	series_title = soup.select("#area_main .box-series .post-items .post-title a")[0].getText().rstrip() # シリーズ名
	article_title = soup.select(".article-title")[0].getText().strip() # 記事名
	article_id = article_url.rsplit("/")[-1] # 記事ID

	dirname = os.path.join(author, series_title)
	dirname_fullpath = os.path.join(root_dir, dirname)
	os.makedirs(dirname_fullpath, exist_ok=True)

	for idx, elm in enumerate(soup.select(".article-content p img")):
		url = elm.get("src")
		try:
			filename = f"{str(series_num)}_{article_title}({article_id})_{str(idx+1)}.png"
			dest = os.path.join(dirname, filename)
			response = requests.get(url)
			image = response.content
			with open(dest, mode="wb") as file:
				file.write(image)
		except Exception as e:
			print(e)

	with open(downloaded_txt, mode="a") as f:
		f.writelines(f"{article_url}\n")

def login(email, password):
	loginpage_url = "https://cakes.mu/user/sign_in"
	login_url = "https://cakes.mu/user/signed_in"

	session = requests.session()
	response = session.get(loginpage_url)
	response_cookie = response.cookies

	bs = BeautifulSoup(response.text, "lxml")
	authenticity_token = bs.find(attrs={'name':'authenticity_token'}).get('value')

	utf8 = "✓"
	commit = "ログイン"

	login_info = {"email": email, "password": password, "utf8": utf8, "commit": commit, "authenticity_token": authenticity_token}
	result = session.post(login_url, data=login_info, cookies=response_cookie)
	return result.cookies


if __name__ == "__main__":

	logined_cookie = login(EMAIL, PASSWORD)

	# 開発中なのでとりあえずハードコーディング, 4513は恋愛マトリョシカガール
	serialization_id = 4513

	root_dir = os.path.dirname(os.path.abspath(__file__))
	downloaded_txt = os.path.join(root_dir, "downloaded.txt")

	os.chdir(root_dir)

	if not os.path.isfile(downloaded_txt):
		with open(downloaded_txt, mode="w") as f:
			f.write("")

	download_target_urls = get_download_target_urls(serialization_id)
	download_target_urls.sort()

	# 個別ページからの画像DL
	for series_num, download_url in enumerate(download_target_urls):
		download_images(download_url, series_num+1, logined_cookie)
