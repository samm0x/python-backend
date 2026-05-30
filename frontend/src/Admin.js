import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

function Admin() {
  const [me, setMe] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const checkAdmin = async () => {
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
      if (data.role !== "admin") return navigate("/");

      setMe(data);
    };

    checkAdmin();
  }, [navigate]);

  if (!me) return <p className="p-8 text-center">در حال بررسی دسترسی ادمین...</p>;

  return (
    <div className="p-8 bg-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-6 text-center text-red-500">
        پنل ادمین 🔥
      </h1>
      <div className="max-w-3xl mx-auto bg-white p-6 rounded shadow-md">
        <p className="text-xl font-semibold mb-2">Welcome, {me.username}</p>
        <p className="mb-4">Role: {me.role}</p>

        <button
          onClick={() => alert("عملیات ادمین")}
          className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 transition"
        >
          انجام عملیات ادمین
        </button>
      </div>
    </div>
  );
}

export default Admin;