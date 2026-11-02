"""
TapTapTyping — Load Test
Run: locust -f locustfile.py --host=http://127.0.0.1:8000
UI:  http://localhost:8089
"""
from locust import HttpUser, task, between


class NormalVisitor(HttpUser):
    """Simulates a real user browsing the site."""
    wait_time = between(1, 3)

    @task(5)
    def home(self):
        self.client.get("/", name="🏠 Home/Leaderboard")

    @task(4)
    def typing_test(self):
        self.client.get("/taptap/", name="⌨️ Typing Test")

    @task(3)
    def blogs(self):
        self.client.get("/blogs/", name="📝 Blog List")

    @task(3)
    def lessons(self):
        self.client.get("/typing-lessons/", name="📚 Lessons")

    @task(2)
    def login_page(self):
        self.client.get("/login/", name="🔐 Login")

    @task(2)
    def signup_page(self):
        self.client.get("/signup/", name="✍️ Signup")

    @task(1)
    def faq(self):
        self.client.get("/FAQ/", name="❓ FAQ")

    @task(1)
    def about(self):
        self.client.get("/aboutus/", name="ℹ️ About")

    @task(1)
    def jobs(self):
        self.client.get("/jobs/", name="💼 Jobs")

    @task(1)
    def sitemap(self):
        self.client.get("/sitemap.xml", name="🗺️ Sitemap")

    @task(1)
    def robots(self):
        self.client.get("/robots.txt", name="🤖 Robots.txt")
