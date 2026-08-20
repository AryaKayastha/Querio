import { Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage/LandingPage.jsx";
import ChatPage from "./pages/ChatPage/ChatPage.jsx";
import WidgetDemoPage from "./pages/WidgetDemoPage/WidgetDemoPage.jsx";

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/chat" element={<ChatPage />} />
      <Route path="/widget" element={<WidgetDemoPage />} />
    </Routes>
  );
};

export default App;
