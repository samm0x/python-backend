import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

function Dashboard() {
  const [me, setMe] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const getMe = async () => {
      const token = localStorage.getItem("token");
      if (!token) return navigate("/login");

      const res = await fetch("http://127.0.0.1:8000/me", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        localStorage.removeItem("token");
        return navigate("/login");
      }

      const data = await res.json();
      setMe(data);
    };

    getMe();
  }, [navigate]);

  if (!me) return <p className="p-8 text-center">در حال لود...</p>;

  return (
    <div className="p-8 bg-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-6 text-center">Dashboard</h1>

      <div className="max-w-3xl mx-auto grid gap-6 sm:grid-cols-1 md:grid-cols-2">
        {/* کارت کاربر */}
        <div
          className={`p-6 rounded-lg shadow-md ${
            me.role === "admin" ? "bg-red-500 text-white" : "bg-white"
          }`}
        >
          <h2 className="text-xl font-semibold mb-2">{me.username}</h2>
          <p className="mb-4">Role: {me.role}</p>

          {me.role === "admin" && (
            <button
              onClick={() => navigate("/admin")}
              className="bg-yellow-400 text-black px-4 py-2 rounded hover:bg-yellow-500 transition"
            >
              ورود به پنل ادمین 🔥
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;