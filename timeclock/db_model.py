from sqlalchemy import BigInteger, Boolean, Column, Float, ForeignKey, Integer, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

__all__ = ("Guild", "Role", "Member", "Time", "async_session", "create_db")


# Create a Base class for our Model class definitions
Base = declarative_base()


class Guild(Base):
    """
    Represents the guild table from the database. This table stores config
    information about the guild

    Attributes
    ----------
    id: :type:`BigInteger`
        Guild's Discord ID
    message_id: :type:`BigInteger`
        Discord ID for the message where the embed is located
    embed: :type:`Text`
        The serialized embed the guild is using for their Punch In/Out message
    members: :type:`relationship('Member')`
        List of members associated with this guild
    roles :type:`relationship('Role')`
        The relationship to the Role table that stores guild roles allowed to use punch button and mod roles
    """

    __tablename__ = "guild"

    id = Column(BigInteger, primary_key=True)
    message_id = Column(BigInteger, nullable=True)
    channel_id = Column(BigInteger, nullable=True)
    embed = Column(Text, nullable=True)
    members = relationship("Member")
    roles = relationship("Role")

    __mapper_args__ = {"eager_defaults": True}


class Role(Base):
    """
    Represents the role table within the database. This table is responsible for storing all role IDs
    the guild has configured for mod_role or roles allowed to use the punch buttons

    id: :type:`BigInteger`
        Role's Discord ID
    guild_id: :type:`BigInteger`
        Guild's Discord ID - related to the guild.id column in guild table
    is_mod: :type:`Boolean`
        True if this role is a mod role
    can_punch: :type:`Boolean`
        True if this role is allowed to punch
    """

    __tablename__ = "role"

    id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey("guild.id"))
    is_mod = Column(Boolean, nullable=False)
    can_punch = Column(Boolean, nullable=False)


class Member(Base):
    """
    Represents the member table from the database. This table stores members and has a relationship
    for the member to it's times within the time table

    Attributes
    ----------
    id: :type:`BigInteger`
        Member's Discord ID
    guild_id: :type:`BigInteger`
        Guild's Discord ID - related to the guild.id column in the guild table
    on_duty: :type:`Boolean`
        True if the member is on duty, else False
    times: :type:`relationship('Time')`
        Relationship to the Time table that stores the member punch in and out times
    """

    __tablename__ = "member"

    id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey("guild.id"))
    on_duty = Column(Boolean, nullable=False)
    times = relationship("Time")

    __mapper_args__ = {"eager_defaults": True}


class Time(Base):
    """
    Represents the time table within the database. This table is responsible for storing
    member punch in and out times

    Attributes
    id: :type:`Integer`
        Row ID generated by the database
    punch_in: :type:`TIMESTAMP`
        The unix timestamp (as UTC) for when the member punched in
    punch_out: :type:`TIMESTAMP`
        The unix timestamp (as UTC) for when the member punched out
    """

    __tablename__ = "time"

    id = Column(Integer, primary_key=True)
    member_id = Column(BigInteger, ForeignKey("member.id"))
    punch_in = Column(Float, nullable=False)
    punch_out = Column(Float, nullable=True, default=None)


# engine = create_async_engine("sqlite+aiosqlite:///database/data.sqlite3", echo=False)
engine = create_async_engine("sqlite+aiosqlite:///timeclock/database/data.sqlite3", echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def create_db(engine=engine, Base=Base):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


if __name__ == "__main__":
    import asyncio

    engine = create_async_engine("sqlite+aiosqlite:///database/data.sqlite3", echo=True)
    asyncio.run(create_db(engine, Base))
