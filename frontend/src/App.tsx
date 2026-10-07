import { Route, Routes } from "react-router-dom";
import { Navbar } from "./components/ui";
import Home from "./pages/Home"; import Dashboard from "./pages/Dashboard"; import Setup from "./pages/Setup";
import Live from "./pages/Live"; import ReportPage from "./pages/Report"; import History from "./pages/History";
export default function App() {
  return (<><Navbar /><main className="mx-auto max-w-6xl px-4 py-8"><Routes>
    <Route path="/" element={<Home />} /><Route path="/dashboard" element={<Dashboard />} /><Route path="/setup" element={<Setup />} />
    <Route path="/interview/:id" element={<Live />} /><Route path="/report/:id" element={<ReportPage />} /><Route path="/history" element={<History />} />
  </Routes></main></>);
}
