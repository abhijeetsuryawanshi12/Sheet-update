import sqlalchemy
from databases import Database
from app.config import settings

# Create a Database instance for async connections
database = Database(settings.DATABASE_URL)

# SQLAlchemy metadata is a collection of Table objects and their associated schema
metadata = sqlalchemy.MetaData()

# Define the 'companies' table schema.
# This MUST match the table structure in your Neon DB.
# The column names here should be the "clean" names we want to use in the code.
companies = sqlalchemy.Table(
    "companies",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("website", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("latest_funding", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("latest_funding_date", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("total_funding", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("investors", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("valuation", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("overview", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("sector", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("sinarmas_interest", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("implied_valuation", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("share_transfer_allowed", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("liquidity_ez", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("liquidity_forge", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("liquidity_nasdaq", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("summary", sqlalchemy.Text, nullable=True),
    sqlalchemy.Column("sellers_ask", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("buyers_bid", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("total_bids", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("total_asks", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("highest_bid_price", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("lowest_ask_price", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("price_history", sqlalchemy.Text, nullable=True), # Storing JSON as text
    sqlalchemy.Column("funding_history", sqlalchemy.Text, nullable=True), # Storing JSON as text
)

# You can add engine creation here if you need to create tables,
# but since your data is already in Neon, we just need the definition.
# engine = sqlalchemy.create_engine(settings.DATABASE_URL)
# metadata.create_all(engine) # This line would create the table if it didn't exist