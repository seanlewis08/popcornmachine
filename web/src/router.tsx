import { createHashRouter } from "react-router-dom";
import { Layout } from "@/components/Layout";
import HomePage from "@/pages/HomePage";
import BoxScorePage from "@/pages/BoxScorePage";
import GameflowPage from "@/pages/GameflowPage";

export const router = createHashRouter([
  {
    element: <Layout />,
    children: [
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
    ],
  },
]);
