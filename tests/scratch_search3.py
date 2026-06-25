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
        
        stmt = (
            select(Paragraph, Chapter)
            .join(Chapter, Paragraph.chapter_id == Chapter.id)
            .where(
                Chapter.version_id == fic.active_version_id,
                Chapter.chapter_number == 126,
                Paragraph.text.ilike(f"%Harry would automatically become a Black if he were disowned as a Potter.%")
            )
        )
        res = await session.execute(stmt)
        for row in res:
            para = row[0]
            print(f"Para ID: {para.id}, Number: {para.paragraph_number}")
            print(f"Text: {para.text[:50]}...")

if __name__ == "__main__":
    asyncio.run(main())
