"""Space Fractions: a desktop fraction-learning game.

Package layout mirrors the microservice boundaries from the architecture:
    model   -> Game, Question, User, Admin entities (domain)
    services-> GameService, QuestionService, UserService, AdminService
    storage -> PostgreSQL adapter + optional SQLite offline adapter
    ui      -> tkinter desktop controller + views (kept separate from logic)
"""

__version__ = "1.0.0"
