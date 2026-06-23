import asyncio
import os
import config
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from database.models import Fic, Chapter, Paragraph

load_dotenv()

async def main():
    db_url = os.getenv("DATABASE_URL")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    db_url = db_url.replace("sslmode=require", "")

    engine = create_async_engine(db_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    async with session_maker() as session:
        result = await session.execute(select(Fic).where(Fic.active_version_id != None))
        fic = result.scalars().first()
        
        stmt = (
            select(Paragraph)
            .join(Chapter, Paragraph.chapter_id == Chapter.id)
            .where(
                Chapter.version_id == fic.active_version_id,
                Chapter.chapter_number == 126,
                Paragraph.text.ilike(f"%Harry would automatically become a Black if he were disowned as a Potter.%")
            )
        )
        res = await session.execute(stmt)
        paras = res.scalars().all()
        print(f"Matched {len(paras)} paras")
        for p in paras:
            print(f"Para: {p.paragraph_number}")
            print(f"Text: {p.text}")
            
if __name__ == "__main__":
    asyncio.run(main())
