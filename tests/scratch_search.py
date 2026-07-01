import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from database.models import Fic, Chapter, Paragraph
from dotenv import load_dotenv

load_dotenv()


async def main():
    db_url = os.getenv("DATABASE_URL").replace("postgres://", "postgresql+asyncpg://")
    db_url = db_url.replace("sslmode=require", "")
    engine = create_async_engine(db_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        result = await session.execute(select(Fic).where(Fic.active_version_id != None))
        fic = result.scalars().first()

        # Chapter 126
        result = await session.execute(
            select(Chapter).where(
                Chapter.version_id == fic.active_version_id,
                Chapter.chapter_number == 126,
            )
        )
        ch_126 = result.scalars().first()

        # Chapter 80
        result = await session.execute(
            select(Chapter).where(
                Chapter.version_id == fic.active_version_id,
                Chapter.chapter_number == 80,
            )
        )
        ch_80 = result.scalars().first()

        if ch_126:
            result = await session.execute(
                select(Paragraph).where(Paragraph.chapter_id == ch_126.id)
            )
            paras = sorted(result.scalars().all(), key=lambda p: p.paragraph_number)
            print("--- CH 126 ---")
            for p in paras:
                if (
                    "disown" in p.text.lower()
                    or "prince of slytherin" in p.text.lower()
                    or "black" in p.text.lower()
                ):
                    print(f"[{p.paragraph_number}] {p.text}")

        if ch_80:
            result = await session.execute(
                select(Paragraph).where(Paragraph.chapter_id == ch_80.id)
            )
            paras = sorted(result.scalars().all(), key=lambda p: p.paragraph_number)
            print("--- CH 80 ---")
            for p in paras:
                if (
                    "regulus" in p.text.lower()
                    or "horcrux" in p.text.lower()
                    or "locket" in p.text.lower()
                ):
                    print(f"[{p.paragraph_number}] {p.text}")


if __name__ == "__main__":
    asyncio.run(main())
