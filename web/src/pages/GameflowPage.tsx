import { useParams } from "react-router-dom";

export default function GameflowPage() {
  const { gameId } = useParams<{ gameId: string }>();
  return <div className="p-4"><h1 className="text-2xl font-bold">Gameflow: {gameId}</h1></div>;
}
