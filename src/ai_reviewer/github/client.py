from __future__ import annotations

from typing import Any

import httpx


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, owner: str, repo: str) -> None:
        self.owner = owner
        self.repo = repo
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def get_pull_request(self, pull_number: int) -> dict[str, Any]:
        resp = await self._client.get(f"/repos/{self.owner}/{self.repo}/pulls/{pull_number}")
        resp.raise_for_status()
        return resp.json()

    async def get_pull_diff(self, pull_number: int) -> str:
        resp = await self._client.get(
            f"/repos/{self.owner}/{self.repo}/pulls/{pull_number}",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        resp.raise_for_status()
        return resp.text

    async def list_review_comments(self, pull_number: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        page = 1
        while True:
            resp = await self._client.get(
                f"/repos/{self.owner}/{self.repo}/pulls/{pull_number}/comments",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            comments.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return comments

    async def list_issue_comments(self, pull_number: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        page = 1
        while True:
            resp = await self._client.get(
                f"/repos/{self.owner}/{self.repo}/issues/{pull_number}/comments",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            comments.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return comments

    async def update_review_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        resp = await self._client.patch(
            f"/repos/{self.owner}/{self.repo}/pulls/comments/{comment_id}",
            json={"body": body},
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_review_comment(self, comment_id: int) -> None:
        resp = await self._client.delete(
            f"/repos/{self.owner}/{self.repo}/pulls/comments/{comment_id}"
        )
        resp.raise_for_status()

    async def create_pull_review(
        self,
        pull_number: int,
        body: str,
        comments: list[dict[str, Any]],
        event: str = "COMMENT",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"body": body, "event": event}
        if comments:
            payload["comments"] = comments
        resp = await self._client.post(
            f"/repos/{self.owner}/{self.repo}/pulls/{pull_number}/reviews",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    async def create_issue_comment(self, pull_number: int, body: str) -> dict[str, Any]:
        resp = await self._client.post(
            f"/repos/{self.owner}/{self.repo}/issues/{pull_number}/comments",
            json={"body": body},
        )
        resp.raise_for_status()
        return resp.json()

    async def update_issue_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        resp = await self._client.patch(
            f"/repos/{self.owner}/{self.repo}/issues/comments/{comment_id}",
            json={"body": body},
        )
        resp.raise_for_status()
        return resp.json()
