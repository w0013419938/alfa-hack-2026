import { Button, Center } from "@mantine/core";
import { Link } from "react-router-dom";

import { EmptyState } from "../components/States";

export function NotFoundPage() {
  return (
    <Center mih="80vh">
      <EmptyState
        title="Такой страницы нет"
        text="Ссылка устарела или в ней опечатка. Вернитесь в кабинет."
        action={
          <Button component={Link} to="/">
            В кабинет
          </Button>
        }
      />
    </Center>
  );
}
