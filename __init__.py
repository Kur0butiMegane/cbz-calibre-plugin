from calibre.customize.conversion import OutputFormatPlugin
from calibre.ptempfile import TemporaryDirectory
from calibre.utils.zipfile import ZipFile

from os import path

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tif",
}

class OrderedCBZOutput(OutputFormatPlugin):
    name = "Sorted CBZ Output"
    author = "k.megane"
    version = (0, 0, 1)
    file_type = "cbz"
    commit_name = "sorted_cbz_output"

    def convert(self, oeb_book, output_path, input_plugin, opts, log):

        seen = set()
        images = []

        #
        # Cover image
        #

        self._add_cover_image(
            oeb_book,
            seen,
            images,
        )

        #
        # Spine order
        #

        for spine_item in oeb_book.spine:

            root = spine_item.data

            for elem in root.xpath(
                '//*[local-name()="img" or local-name()="image"]'
            ):

                if elem.tag.endswith("img"):
                    src = elem.get("src")
                else:
                    src = (
                        elem.get("href")
                        or elem.get("{http://www.w3.org/1999/xlink}href")
                    )

                if not src:
                    continue

                self._add_image(
                    oeb_book,
                    spine_item,
                    src,
                    seen,
                    images
                )

        with ZipFile(output_path, mode="w") as cbz:
            with TemporaryDirectory("_img_extract_") as tdir:

                for index, image_item in enumerate(images, start=1):

                    ext = self._get_extension(image_item)

                    temp_name = path.join(
                        tdir,
                        f"{index:05d}{ext}"
                    )

                    with open(temp_name, "wb") as f:
                        f.write(image_item.data)

                    cbz.write(
                        temp_name,
                        f"{index:05d}{ext}"
                    )

    def _add_cover_image(
        self,
        oeb_book,
        seen,
        images,
    ):

        #
        # metadata.cover
        #

        try:
            if getattr(oeb_book.metadata, "cover", None):
                cover_id = str(oeb_book.metadata.cover[0])

                for item in oeb_book.manifest:
                    if item.id == cover_id:
                        if item.media_type.startswith("image"):
                            seen.add(item.href)
                            images.append(item)
                            return
        except Exception:
            pass

        #
        # guide['cover']
        #

        try:
            cover_ref = oeb_book.guide["cover"]

            cover_item = oeb_book.manifest.hrefs.get(
                cover_ref.href
            )

            if (
                cover_item is not None
                and cover_item.media_type.startswith("image")
            ):
                seen.add(cover_item.href)
                images.append(cover_item)
                return

        except Exception:
            pass

    def _add_image(
        self,
        oeb_book,
        spine_item,
        src,
        seen,
        images
    ):
        try:
            href = spine_item.abshref(src)
        except Exception:
            return

        image_item = oeb_book.manifest.hrefs.get(href)

        if image_item is None:
            return

        if not image_item.media_type.startswith("image"):
            return

        if image_item.href in seen:
            return

        seen.add(image_item.href)
        images.append(image_item)

    def _get_extension(self, image_item):
        # 元ファイル名の拡張子を優先
        ext = path.splitext(image_item.href.split("?")[0])[1]

        if ext:
            return ext.lower()

        # 拡張子が無い場合は MIME Type から推定
        return MIME_TO_EXT.get(
            image_item.media_type.lower(),
            ".img"
        )