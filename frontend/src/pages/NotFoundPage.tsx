import { Button, Center } from "@mantine/core";
import { Link } from "react-router-dom";

import { EmptyState } from "../components/States";

export function NotFoundPage() {
  return (
    <Center mih="80vh">
      <EmptyState
        title="Такой страницы нет"
        text="Возможно, ссылка устарела. Вернитесь в кабинет."
        action={
          <Button component={Link} to="/">
            В кабинет
          </Button>
        }
      />
    </Center>
  );
}
