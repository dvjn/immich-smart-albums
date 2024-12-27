#!/usr/bin/env python

import requests
import yaml
from pydantic import BaseModel, HttpUrl, StringConstraints, Field
from typing_extensions import Annotated
from loguru import logger
from time import sleep


class SmartAlbumConfig(BaseModel):
    album_id: Annotated[str, StringConstraints(min_length=1)]
    search_params: dict


class Config(BaseModel):
    interval: int = Field(default=3600)
    url: HttpUrl
    api_key: Annotated[str, StringConstraints(min_length=1)]
    albums: list[SmartAlbumConfig]


class ImmichAPI:
    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key

    def _get_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }

    def search_assets_by_metadata(self, params: dict) -> list[dict]:
        assets = []

        response = requests.post(
            self.url + "/api/search/metadata",
            headers=self._get_headers(),
            json=params,
        )
        data = response.json()
        assets.extend(data["assets"]["items"])

        while data["assets"]["nextPage"] is not None:
            response = requests.post(
                self.url + "/api/search/metadata",
                headers=self._get_headers(),
                json={"page": data["assets"]["nextPage"], **params},
            )
            data = response.json()
            assets.extend(data["assets"]["items"])

        return assets

    def get_album_assets(self, album_id: str) -> dict:
        response = requests.get(
            self.url + "/api/albums/" + album_id,
            headers=self._get_headers(),
        )
        data = response.json()
        return data["assets"]

    def add_assets_to_album(self, album_id: str, asset_ids: list[str]) -> bool:
        response = requests.put(
            self.url + "/api/albums/" + album_id + "/assets",
            headers=self._get_headers(),
            json={"ids": asset_ids},
        )
        data = response.json()
        return all(asset["success"] for asset in data)


def load_config() -> Config:
    with open("config.yaml", "r") as f:
        raw_config = yaml.safe_load(f)
        return Config(**raw_config)


def process_album(api: ImmichAPI, album_id: str, search_params: dict):
    found_assets = api.search_assets_by_metadata(search_params)
    logger.info(f"Found {len(found_assets)} assets from search.")
    found_asset_ids = set(asset["id"] for asset in found_assets)

    album_assets = api.get_album_assets(album_id)
    logger.info(f"Found {len(album_assets)} assets from album.")
    album_asset_ids = set(asset["id"] for asset in album_assets)

    assets_to_add = found_asset_ids - album_asset_ids
    logger.info(f"Found {len(assets_to_add)} assets to add to the album.")

    if not assets_to_add:
        logger.info("No assets to add.")
        return

    logger.info("Adding assets to the album.")
    if api.add_assets_to_album(album_id, list(assets_to_add)):
        logger.info(f"Added {len(assets_to_add)} assets to the album.")
    else:
        logger.error("Failed to add assets to the album.")


@logger.catch
def main():
    logger.info("Loading configuration.")
    config = load_config()

    api = ImmichAPI(str(config.url), config.api_key)

    while True:
        for album in config.albums:
            logger.info(f"Processing album: {album.album_id}")
            process_album(api, album.album_id, album.search_params)
        logger.info(f"Sleeping for {config.interval} seconds.")
        sleep(config.interval)


if __name__ == "__main__":
    main()
