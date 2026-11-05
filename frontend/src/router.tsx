import { Navigate, type RouteObject } from "react-router"
import { RequireAuth, RequireGuest } from "@/components/auth/RouteGuards"
import AdminPage from "@/routes/AdminPage"
import AssistantDetailPage from "@/routes/AssistantDetailPage"
import AssistantPickerPage from "@/routes/AssistantPickerPage"
import AuthLayout from "@/routes/AuthLayout"
import ChatLayout from "@/routes/ChatLayout"
import ChatPage from "@/routes/ChatPage"
import GlobalError from "@/routes/GlobalError"
import LoginPage from "@/routes/LoginPage"
import NotFound from "@/routes/NotFound"
import PickerLayout from "@/routes/PickerLayout"
import ProfilePage from "@/routes/ProfilePage"
import RootLayout from "@/routes/RootLayout"
import RouteError from "@/routes/RouteError"
import SignupPage from "@/routes/SignupPage"
import ThreadsListPage from "@/routes/ThreadsListPage"

export const routes: RouteObject[] = [
  {
    element: <RootLayout />,
    errorElement: <GlobalError />,
    children: [
      {
        errorElement: <RouteError />,
        children: [
          {
            element: <RequireGuest />,
            children: [
              {
                element: <AuthLayout />,
                children: [
                  { path: "login", element: <LoginPage /> },
                  { path: "signup", element: <SignupPage /> },
                ],
              },
            ],
          },
          {
            element: <RequireAuth />,
            children: [
              { index: true, element: <Navigate to="/assistants" replace /> },
              {
                element: <PickerLayout />,
                children: [{ path: "assistants", element: <AssistantPickerPage /> }],
              },
              {
                element: <ChatLayout />,
                children: [
                  { path: "profile", element: <ProfilePage /> },
                  { path: "admin", element: <AdminPage /> },
                  { path: "assistants/:id", element: <AssistantDetailPage /> },
                  { path: "assistants/:id/threads", element: <ThreadsListPage /> },
                  { path: "assistants/:id/threads/:threadId", element: <ChatPage /> },
                ],
              },
              { path: "*", element: <NotFound /> },
            ],
          },
        ],
      },
    ],
  },
]
