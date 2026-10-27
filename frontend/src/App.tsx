import { Routes, Route } from "react-router-dom";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Signup } from "./pages/Signup";
import { Dashboard } from "./pages/Dashboard";
import { CreatePoll } from "./pages/CreatePoll";
import { Room } from "./pages/Room";
import { Join } from "./pages/Join";
import { Results } from "./pages/Results";
import { ProtectedRoute } from "./components/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/create"
        element={
          <ProtectedRoute>
            <CreatePoll />
          </ProtectedRoute>
        }
      />
      <Route path="/room/:code" element={<Room />} />
      <Route path="/join/:code" element={<Join />} />
      <Route path="/results/:code" element={<Results />} />
    </Routes>
  );
}
