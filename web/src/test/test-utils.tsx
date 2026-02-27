import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import type { RenderOptions } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

interface RenderWithRouterOptions extends Omit<RenderOptions, "wrapper"> {
  initialPath?: string;
}

export function renderWithRouter(
  ui: ReactElement,
  { initialPath = "/", ...renderOptions }: RenderWithRouterOptions = {}
) {
  return render(ui, {
    wrapper: ({ children }) => (
      <MemoryRouter initialEntries={[initialPath]}>{children}</MemoryRouter>
    ),
    ...renderOptions,
  });
}
