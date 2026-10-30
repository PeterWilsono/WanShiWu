import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    /** 需要有效登录状态才能访问。 */
    requiresAuth?: boolean
    /** 仅未登录访问，例如登录页；已登录用户会被送回首页。 */
    guestOnly?: boolean
  }
}

export {}
