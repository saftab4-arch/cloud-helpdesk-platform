from flask import Flask, request, redirect
import os
import psycopg2

app = Flask(__name__)


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open'
        );
        """
    )
    conn.commit()
    cur.close()
    conn.close()


@app.route("/health")
def health():
    return "healthy", 200


@app.route("/", methods=["GET", "POST"])
def tickets():
    init_db()

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        priority = request.form["priority"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tickets (title, description, priority) VALUES (%s, %s, %s)",
            (title, description, priority),
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, description, priority, status FROM tickets ORDER BY id DESC")
    tickets = cur.fetchall()
    cur.close()
    conn.close()

    ticket_rows = ""
    for ticket in tickets:
        ticket_rows += f"""
        <tr>
            <td>{ticket[0]}</td>
            <td>{ticket[1]}</td>
            <td>{ticket[2]}</td>
            <td>{ticket[3]}</td>
            <td>{ticket[4]}</td>
        </tr>
        """

    return f"""
    <h1>Help Desk Ticket System</h1>

    <form method="POST">
        <input name="title" placeholder="Ticket title" required><br><br>
        <textarea name="description" placeholder="Ticket description" required></textarea><br><br>
        <select name="priority">
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
        </select><br><br>
        <button type="submit">Create Ticket</button>
    </form>

    <h2>Tickets</h2>
    <table border="1" cellpadding="8">
        <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Description</th>
            <th>Priority</th>
            <th>Status</th>
        </tr>
        {ticket_rows}
    </table>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
