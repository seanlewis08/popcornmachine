import { useParams } from "react-router-dom";

export default function BoxScorePage() {
  const { gameId } = useParams<{ gameId: string }>();
  return <div className="p-4"><h1 className="text-2xl font-bold">Box Score: {gameId}</h1></div>;
}
