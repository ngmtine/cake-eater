import os
import configparser
import requests
from bs4 import BeautifulSoup

def read_settings():
	"""settings.iniを読み込みます"""
	try:
		ini = configparser.ConfigParser()
		ini.read("settings.ini", encoding="utf-8_sig")
		email = ini["env"]["email"]
		password = ini["env"]["password"]
		serialization_ids = []
		_serialization_ids = ini["serialization_id"]["idlist"]
		for i in _serialization_ids.split(","):
			if i:
				serialization_ids.append(f"{i.strip()}")
	except Exception as e:
		print(f"{e}\nsettings.ini読み込みエラーだよ～ちゃんと用意してね～")
		exit()
	
	return email, password, serialization_ids

def login(email, password):
	"""ログイン成功ならクッキーを返す、失敗ならNoneを返す"""

	loginpage_url = "https://cakes.mu/user/sign_in"
	login_url = "https://cakes.mu/user/signed_in"

	session = requests.session()
	loginpage = session.get(loginpage_url)

	bs = BeautifulSoup(loginpage.text, "lxml")
	authenticity_token = bs.find(attrs={'name':'authenticity_token'}).get('value')

	payload = {"email": email, "password": password, "authenticity_token": authenticity_token, "utf8": "✓", "commit": "ログイン"}
	try:
		login_result = session.post(login_url, data=payload, cookies=loginpage.cookies)
	except Exception as e:
		print(e)
	
	bs = BeautifulSoup(login_result.text, "lxml")
	if not bs.select(".error-message"): # ログインの成否判定、ここもうちょいうまいことしたい
		return login_result.cookies
	else:
		return None	

class CakeEater:
	"""
	serialization_idを受け取り、記事内の画像をDLします

	Parameters:
		serialization_id: str
		cookie: str

	Instance Variables:
		self.download_target_urls: list
	"""
	def __init__(self, serialization_id, cookie):
		self.serialization_id, self.cookie = serialization_id, cookie
		self.download_target_urls = self.get_download_target_urls()
		self.author, self.series_title = self.get_series_info() # 第1話ページから著者名とシリーズ名を取得
		self.mkdir_chdir()
		self.downloaded_list = self.get_downloaded_list()

	def get_download_target_urls(self):
		""" 連載固有のID（serialization_id）から、ダウンロード対象のページURLを取得し、リストで返します """
		_download_target_urls = []
		page_num = 0
		while True:
			page_num += 1
			request_url = f"https://cakes.mu/series/posts_pager?page={page_num}&sort=&serialization_id={self.serialization_id}"
			response = requests.get(request_url)
			soup = BeautifulSoup(response.text,'lxml')
			pages = soup.select(".post-title-full a")

			if pages == []: # if response.status_code == 404: では判定ができないことに注意
				break

			while pages:
				try:
					article = pages.pop()
					relative_url = article.get("href")
					url = f"https://cakes.mu{relative_url}"
					_download_target_urls.append(url)
				except Exception as e:
					print(e)
		
		_download_target_urls.sort() # ソート

		return _download_target_urls

	def get_series_info(self):
		"""第1話ページから著者名とタイトルを取得"""
		firstpage_url = self.download_target_urls[0]
		response = requests.get(firstpage_url)
		soup = BeautifulSoup(response.text,'lxml')

		author = soup.find("meta", attrs={"name": "author"})["content"] # 著者
		series_title = soup.select("#area_main .box-series .post-items .post-title a")[0].getText().rstrip() # シリーズ名

		return author, series_title

	def mkdir_chdir(self):
		"""カレントディレクトリにダウンロード先フォルダの作成と移動"""
		dest_dir = os.path.join(os.getcwd(), self.series_title)
		os.makedirs(dest_dir, exist_ok=True)
		os.chdir(dest_dir)

	def get_downloaded_list(self):
		"""カレントディレクトリのdownloaded.txtの作成と読み込み"""
		downloaded_txt = os.path.join(os.getcwd(), "downloaded.txt")

		# downloaded.txtの作成
		if not os.path.isfile(downloaded_txt):
			with open(downloaded_txt, mode="w") as f:
				f.write("")

		# downloaded.txtの読み込み
		with open(downloaded_txt, mode="r") as f:
			downloaded_list = list(map(lambda i: i.rstrip(), f.readlines()))

		return downloaded_list

	def download_starter(self, article_url, series_num):
		"""個別ページのurlから画像をダウンロードします
		series_numは連載の中の何話目かを示す変数であるが、
		cakesは連載ごとにそのページが第何話なのか特定できるシリーズ番号を振っていない？のでこちらで管理する必要がある"""

		if article_url in self.downloaded_list: # ダウンロード済みの場合
			return

		else: # 未ダウンロードの場合
			self.download_images(article_url, series_num)
			self.append_downloaded_txt(article_url)

	def download_images(self, article_url, series_num):
		response = requests.get(article_url, cookies=self.cookie)
		soup = BeautifulSoup(response.text,'lxml')
		# article_id = article_url.rsplit("/")[-1] # 記事ID

		title = soup.select("title")[0].text
		for idx, elm in enumerate(soup.select(".article-content p img")):
			url = elm.get("src")
			try:
				filename = f"{str(series_num)}_{self.series_title}_{title}_{str(idx+1)}.png" # 現在はpng以外の拡張子を想定してない
				response = requests.get(url)
				image = response.content
				with open(filename, mode="wb") as file:
					file.write(image)
			except Exception as e:
				print(e)

	def append_downloaded_txt(self, article_url):
		with open("downloaded.txt", mode="a") as f:
			f.writelines(f"{article_url}\n")

def main():
	root_dir = os.path.dirname(os.path.abspath(__file__))
	os.chdir(root_dir)

	email, password, serialization_ids = read_settings()
	cookie = login(email, password)
	if cookie:
		print("★ ログイン成功しました。ダウンロード開始します。")
	else:
		print("★ ログイン失敗しました。無料記事のみダウンロード開始します。")

	for serialization_id in serialization_ids:
		os.chdir(root_dir)
		Series = CakeEater(serialization_id, cookie)

		print(f"★ {Series.author}, {Series.series_title} のダウンロードを開始します")
		for series_num, article_url in enumerate(Series.download_target_urls):
			Series.download_starter(article_url, series_num+1)

		# print(f"★ {author}, {series_title} のダウンロードが完了しました")

if __name__ == "__main__":
	print("★ starting cake-eater...")
	main()
	print("★ オワリ")