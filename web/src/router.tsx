import { createHashRouter } from "react-router-dom";
import HomePage from "@/pages/HomePage";
import BoxScorePage from "@/pages/BoxScorePage";
import GameflowPage from "@/pages/GameflowPage";

export const router = createHashRouter([
  {
    path: "/",
    element: <HomePage />,
  },
  {
    path: "/game/:gameId/boxscore",
    element: <BoxScorePage />,
  },
  {
    path: "/game/:gameId/gameflow",
    element: <GameflowPage />,
  },
]);
